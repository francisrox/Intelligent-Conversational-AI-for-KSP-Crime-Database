from fastapi import APIRouter
from app.services.trend_queries import get_dashboard

router = APIRouter()


@router.get("/dashboard")
def dashboard():
    """Everything Module 3's dashboard needs in one call: counts by crime type,
    by district, by investigation status, a monthly timeline, and per-station
    hotspot coordinates for the map."""
    return get_dashboard()
