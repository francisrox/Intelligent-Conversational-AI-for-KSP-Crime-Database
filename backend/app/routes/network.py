from fastapi import APIRouter, Query, Depends
from app.services.network_queries import (
    get_accused_network,
    get_crime_network,
    get_hidden_connections,
    get_repeat_offenders,
)
from app.services.auth import require_role, log_audit

router = APIRouter()


@router.get("/accused/{accused_id}")
def accused_network(accused_id: int, depth: int = Query(2, ge=1, le=3)):
    """Graph of everything connected to one accused person, out to `depth` hops."""
    return get_accused_network(accused_id, depth)


@router.get("/crime/{crime_id}")
def crime_network(crime_id: int):
    """Graph of everything directly tied to one crime (accused, victim, vehicle)."""
    return get_crime_network(crime_id)


@router.get("/hidden-connections")
def hidden_connections(
    limit: int = Query(25, ge=1, le=100),
    user: dict = Depends(require_role("Admin", "Supervisor", "Investigator")),
):
    """The headline Module 2 query: vehicles shared across different accused,
    in different districts — connections a manual FIR search would likely miss.

    Module 10 demo: this is intelligence data, so it's role-gated (Analyst/Viewer
    cannot access it) and every access is written to audit_log."""
    log_audit(user, "view_hidden_connections", "/api/network/hidden-connections", f"limit={limit}")
    return {"connections": get_hidden_connections(limit)}


@router.get("/repeat-offenders")
def repeat_offenders(limit: int = Query(25, ge=1, le=100)):
    """Accused linked to multiple crimes, ranked by count."""
    return {"offenders": get_repeat_offenders(limit)}
