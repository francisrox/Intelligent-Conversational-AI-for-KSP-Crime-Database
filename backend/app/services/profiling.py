from datetime import date

from app.db import get_connection


def _fetch_accused_crimes(accused_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, age, gender, gang_id, is_repeat_offender FROM accused WHERE id = %s",
        (accused_id,),
    )
    accused_row = cur.fetchone()
    if not accused_row:
        cur.close()
        conn.close()
        return None, []

    cur.execute(
        """SELECT c.id, c.fir_no, c.crime_type, c.crime_date, c.district, c.investigation_status
           FROM crime c JOIN crime_accused ca ON c.id = ca.crime_id
           WHERE ca.accused_id = %s ORDER BY c.crime_date DESC""",
        (accused_id,),
    )
    crimes = cur.fetchall()
    cur.close()
    conn.close()
    return accused_row, crimes


def get_offender_profile(accused_id: int):
    """Deliberately a transparent, hand-weighted formula rather than a trained
    model — for a hackathon, an explainable score beats a black-box one that
    looks impressive but can't justify itself (see Module 9)."""
    accused_row, crimes = _fetch_accused_crimes(accused_id)
    if accused_row is None:
        return None

    aid, name, age, gender, gang_id, flagged_repeat = accused_row
    case_count = len(crimes)

    type_counts = {}
    for c in crimes:
        crime_type = c[2]
        type_counts[crime_type] = type_counts.get(crime_type, 0) + 1
    most_common_type = max(type_counts, key=type_counts.get) if type_counts else None
    most_common_count = type_counts.get(most_common_type, 0)

    most_recent_date = max((c[3] for c in crimes), default=None)
    days_since_last = (date.today() - most_recent_date).days if most_recent_date else None

    # ---- Risk score components — each one capped, weighted, and explained ----
    case_count_points = min(case_count * 5, 40)
    specialization_points = 15 if most_common_count >= 2 else 0
    gang_points = 20 if gang_id is not None else 0

    if days_since_last is None:
        recency_points = 0
    elif days_since_last <= 30:
        recency_points = 25
    elif days_since_last <= 90:
        recency_points = 15
    elif days_since_last <= 180:
        recency_points = 8
    else:
        recency_points = 2

    total_score = case_count_points + specialization_points + gang_points + recency_points

    if total_score >= 70:
        tier = "High"
    elif total_score >= 40:
        tier = "Medium"
    else:
        tier = "Low"

    return {
        "accused_id": aid,
        "name": name,
        "age": age,
        "gender": gender,
        "gang_affiliated": gang_id is not None,
        "flagged_repeat_offender": flagged_repeat,
        "case_count": case_count,
        "most_recent_case_date": str(most_recent_date) if most_recent_date else None,
        "days_since_last_case": days_since_last,
        "risk_score": total_score,
        "risk_tier": tier,
        "risk_breakdown": [
            {
                "factor": "Prior case count",
                "raw_value": f"{case_count} case(s)",
                "points": case_count_points,
                "max_points": 40,
                "explanation": f"{case_count} linked case(s) x 5 points each, capped at 40",
            },
            {
                "factor": "Crime-type specialization",
                "raw_value": f"{most_common_count}x {most_common_type}" if most_common_type else "n/a",
                "points": specialization_points,
                "max_points": 15,
                "explanation": "15 points if the same crime type appears 2+ times (a pattern, not a one-off)",
            },
            {
                "factor": "Gang affiliation",
                "raw_value": "Yes" if gang_id is not None else "No",
                "points": gang_points,
                "max_points": 20,
                "explanation": "20 points if linked to a known gang_id in the database",
            },
            {
                "factor": "Recency of last offense",
                "raw_value": f"{days_since_last} days ago" if days_since_last is not None else "n/a",
                "points": recency_points,
                "max_points": 25,
                "explanation": "More recent activity scores higher: <=30d=25, <=90d=15, <=180d=8, else 2",
            },
        ],
        "cases": [
            {
                "crime_id": c[0],
                "fir_no": c[1],
                "crime_type": c[2],
                "crime_date": str(c[3]),
                "district": c[4],
                "investigation_status": c[5],
            }
            for c in crimes
        ],
    }
