import os
from openai import OpenAI
from app.db import get_connection

client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL"), api_key="ollama")  # api_key unused, required by client lib only
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

SCHEMA_DESCRIPTION = """
Tables:
- crime(id, fir_no, crime_type, ipc_sections, crime_date, crime_time, description,
        investigation_status, district, police_station, latitude, longitude)
- accused(id, name, age, gender, address, gang_id, is_repeat_offender)
- victim(id, name, age, gender, occupation, address)
- crime_accused(crime_id, accused_id)
- crime_victim(crime_id, victim_id)
- vehicle(id, plate_no, vehicle_type, owner_accused_id)
- crime_vehicle(crime_id, vehicle_id)

Notes:
- crime_type values: Burglary, Robbery, Theft, Cybercrime, Assault
- investigation_status values: Open, Solved, Under Investigation
- district values: Bengaluru, Mysuru, Mangaluru, Belagavi, Hubballi
- is_repeat_offender is TRUE/FALSE on the accused table directly — use it, don't
  try to compute repeat-offender status by counting crime_accused rows unless asked
  for a count/threshold that differs from the stored flag.
- "this week" / "this month" means relative to CURRENT_DATE in Postgres — use
  CURRENT_DATE and INTERVAL arithmetic, not hardcoded dates.
- The date column on crime is spelled exactly "crime_date" — do not write
  "crime_data" or any other variant.
"""

SQL_SYSTEM_PROMPT = f"""You are a SQL generator for a PostgreSQL crime database.
Schema:
{SCHEMA_DESCRIPTION}

There are ONLY 7 tables in this database: crime, accused, victim, crime_accused,
crime_victim, vehicle, crime_vehicle. Nothing else exists as a table — in particular,
district, police_station, crime_type, and investigation_status are COLUMNS on the
crime table, NOT separate tables. Never write FROM police_station, FROM district,
JOIN police_station, or anything similar — always filter these as
WHERE crime.police_station = '...' / WHERE crime.district = '...' instead.

Rules:
- Output ONLY a single valid PostgreSQL SELECT query. No explanation, no markdown fences, no comments.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE statements — SELECT only.
- Use table joins ONLY among the 7 real tables listed above (e.g. join crime_accused to link crime and accused).
- Always use single quotes for string literals (e.g. WHERE crime_type = 'Burglary'),
  never double quotes — double quotes in PostgreSQL mean identifiers, not strings.
- If the user's question refers to something from the earlier conversation
  (e.g. "only the solved ones"), apply that filter on top of the previous query's
  intent, using the conversation context you're given.
- If the question is ambiguous or unanswerable from this schema, still output your
  best-effort valid SELECT query rather than refusing — the query result being empty
  is fine, an invalid query is not.

Examples of correctly-formed queries for this schema:

Q: Show burglary cases in Whitefield
A: SELECT * FROM crime WHERE crime_type = 'Burglary' AND police_station = 'Whitefield';

Q: Which accused has the highest number of burglary cases?
A: SELECT a.id, a.name, COUNT(*) AS case_count
   FROM accused a
   JOIN crime_accused ca ON a.id = ca.accused_id
   JOIN crime c ON ca.crime_id = c.id
   WHERE c.crime_type = 'Burglary'
   GROUP BY a.id, a.name
   ORDER BY case_count DESC
   LIMIT 1;

Q: How many cybercrime cases were registered this week?
A: SELECT COUNT(*) FROM crime
   WHERE crime_type = 'Cybercrime'
   AND crime_date >= CURRENT_DATE - INTERVAL '7 days';

Q: Which police station has the highest theft cases?
A: SELECT police_station, COUNT(*) AS case_count
   FROM crime
   WHERE crime_type = 'Theft'
   GROUP BY police_station
   ORDER BY case_count DESC
   LIMIT 1;

Q: (follow-up to "Show burglary cases in Bengaluru") Only the solved ones
A: SELECT * FROM crime
   WHERE crime_type = 'Burglary' AND district = 'Bengaluru'
   AND investigation_status = 'Solved';
"""


def generate_sql(user_question: str, conversation_context: list) -> str:
    context_text = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in conversation_context[-6:]
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": f"Conversation so far:\n{context_text}\n\nNew question: {user_question}"}
        ]
    )
    sql = response.choices[0].message.content.strip()
    # Local models sometimes wrap output in markdown fences — strip them defensively
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def repair_sql(user_question: str, broken_sql: str, error_message: str) -> str:
    """Self-correction: feed the exact Postgres error back to the model and ask it
    to fix its own query. Small local models make occasional typos (wrong column
    names, etc.) — one retry catches most of these without any special-case code."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": f"""Original question: {user_question}

This SQL query was generated but failed:
{broken_sql}

PostgreSQL error:
{error_message}

Output ONLY a corrected single valid PostgreSQL SELECT query that fixes this error.
No explanation, no markdown fences."""}
        ]
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def is_safe_select(sql: str) -> bool:
    """Guardrail: only allow single SELECT statements. Not optional — an LLM
    generating raw SQL is a genuine safety concern even in a hackathon demo."""
    normalized = sql.strip().lower()
    if not normalized.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke", ";--", "--"]
    if any(word in normalized for word in forbidden):
        return False
    # Block stacked queries (a second statement after a semicolon)
    stripped = normalized.rstrip(";").strip()
    if ";" in stripped:
        return False
    return True


def run_query(sql: str):
    conn = get_connection()
    try:
        # Second layer of defense: this session can only ever read.
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def summarize_result(user_question: str, rows: list) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""User asked: "{user_question}"
Query returned {len(rows)} rows. Sample data: {rows[:10]}

Write a short, plain-language summary (2-4 sentences) an investigator would find useful.
Mention the count, and any standout pattern in the sample (e.g. a dominant area or repeat name)."""
        }]
    )
    return response.choices[0].message.content.strip()
