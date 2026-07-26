import os

import numpy as np
from openai import OpenAI

from app.db import get_connection

client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL"), api_key="ollama")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def _fetch_case_context(crime_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT fir_no, crime_type, ipc_sections, crime_date, description,
                  investigation_status, district, police_station
           FROM crime WHERE id = %s""",
        (crime_id,),
    )
    crime_row = cur.fetchone()
    if not crime_row:
        cur.close()
        conn.close()
        return None

    cur.execute(
        """SELECT a.name, a.age, a.is_repeat_offender FROM accused a
           JOIN crime_accused ca ON a.id = ca.accused_id WHERE ca.crime_id = %s""",
        (crime_id,),
    )
    accused_rows = cur.fetchall()

    cur.execute(
        """SELECT v.name FROM victim v
           JOIN crime_victim cv ON v.id = cv.victim_id WHERE cv.crime_id = %s""",
        (crime_id,),
    )
    victim_rows = cur.fetchall()

    cur.close()
    conn.close()

    fir_no, crime_type, ipc, crime_date, description, status, district, station = crime_row
    return {
        "fir_no": fir_no,
        "crime_type": crime_type,
        "ipc_sections": ipc,
        "crime_date": str(crime_date),
        "description": description,
        "status": status,
        "district": district,
        "police_station": station,
        "accused": [{"name": n, "age": a, "repeat_offender": r} for n, a, r in accused_rows],
        "victims": [n for (n,) in victim_rows],
    }


def generate_case_summary(crime_id: int):
    """LLM-generated summary + investigative leads, grounded only in this
    case's actual DB fields — Module 9's 'conclusion + evidence' habit applies
    here too, so the prompt explicitly constrains leads to the facts given."""
    context = _fetch_case_context(crime_id)
    if context is None:
        return None

    prompt = f"""Summarize this case for an investigator and suggest 2-3 concrete investigative leads.
Ground every lead only in the facts given below — do not invent details not present here.

Case: {context['fir_no']} — {context['crime_type']} ({context['ipc_sections']})
Date: {context['crime_date']} | Location: {context['police_station']}, {context['district']}
Status: {context['status']}
Description: {context['description']}
Accused on record: {context['accused']}
Victims on record: {context['victims']}

Respond in exactly two sections:
SUMMARY: (2-3 sentences)
LEADS: (2-3 bullet points)"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"case": context, "analysis": response.choices[0].message.content.strip()}


def _cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def find_similar_cases(crime_id: int, top_k: int = 5):
    """In-memory cosine similarity over precomputed embeddings — fine for a
    dataset this size, no separate vector DB needed for a hackathon."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT embedding FROM crime_embedding WHERE crime_id = %s", (crime_id,))
    target_row = cur.fetchone()
    if not target_row:
        cur.close()
        conn.close()
        return []
    target_embedding = target_row[0]

    cur.execute(
        """SELECT ce.crime_id, ce.embedding, c.fir_no, c.crime_type, c.district,
                  c.police_station, c.investigation_status
           FROM crime_embedding ce JOIN crime c ON c.id = ce.crime_id
           WHERE ce.crime_id != %s""",
        (crime_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    scored = []
    for cid, emb, fir_no, crime_type, district, station, status in rows:
        score = _cosine_similarity(target_embedding, emb)
        scored.append(
            {
                "crime_id": cid,
                "fir_no": fir_no,
                "crime_type": crime_type,
                "district": district,
                "police_station": station,
                "investigation_status": status,
                "similarity": round(score, 4),
            }
        )

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
