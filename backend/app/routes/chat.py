from fastapi import APIRouter
from pydantic import BaseModel
from app.services.nl_to_sql import generate_sql, repair_sql, is_safe_select, run_query, summarize_result
from app.services.context_memory import get_session, add_turn

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/")
def chat(req: ChatRequest):
    context = get_session(req.session_id)
    sql = generate_sql(req.message, context)

    if not is_safe_select(sql):
        return {"error": "Query blocked for safety", "sql": sql}

    try:
        rows = run_query(sql)
    except Exception as first_error:
        # One self-correction attempt: feed the exact DB error back to the model
        repaired_sql = repair_sql(req.message, sql, str(first_error))
        if not is_safe_select(repaired_sql):
            return {"error": "Repaired query blocked for safety", "sql": repaired_sql}
        try:
            rows = run_query(repaired_sql)
            sql = repaired_sql  # report the query that actually worked
        except Exception as second_error:
            return {"error": str(second_error), "sql": repaired_sql, "original_sql": sql}

    summary = summarize_result(req.message, rows)

    add_turn(req.session_id, "user", req.message)
    add_turn(req.session_id, "assistant", f"Returned {len(rows)} rows. {summary}")

    return {
        "sql": sql,          # surfaced now so you can sanity-check it; UI shows it later for Module 9
        "summary": summary,
        "rows": rows[:50],   # cap for UI table
        "row_count": len(rows)
    }
