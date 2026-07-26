from app.db import get_connection


def _query(sql):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def get_dashboard():
    """One combined call for the whole Module 3 dashboard — avoids the frontend
    making 5 separate round trips for data that's always shown together."""

    by_crime_type = _query(
        """SELECT crime_type, COUNT(*) AS count
           FROM crime GROUP BY crime_type ORDER BY count DESC"""
    )

    by_district = _query(
        """SELECT district, COUNT(*) AS count
           FROM crime GROUP BY district ORDER BY count DESC"""
    )

    by_status = _query(
        """SELECT investigation_status, COUNT(*) AS count
           FROM crime GROUP BY investigation_status ORDER BY count DESC"""
    )

    monthly_timeline = _query(
        """SELECT to_char(date_trunc('month', crime_date), 'YYYY-MM') AS month, COUNT(*) AS count
           FROM crime GROUP BY month ORDER BY month"""
    )

    # One marker per police station (averaged coordinates), sized by case count —
    # a readable hotspot map instead of 800 overlapping pins.
    hotspots = _query(
        """SELECT district, police_station,
                  ROUND(AVG(latitude)::numeric, 6) AS lat,
                  ROUND(AVG(longitude)::numeric, 6) AS lng,
                  COUNT(*) AS count
           FROM crime
           GROUP BY district, police_station
           ORDER BY count DESC"""
    )

    return {
        "by_crime_type": by_crime_type,
        "by_district": by_district,
        "by_status": by_status,
        "monthly_timeline": monthly_timeline,
        "hotspots": hotspots,
    }
