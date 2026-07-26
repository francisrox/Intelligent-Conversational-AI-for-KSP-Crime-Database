from fastapi import APIRouter, HTTPException
from app.services.profiling import get_offender_profile

router = APIRouter()


@router.get("/{accused_id}")
def offender_profile(accused_id: int):
    profile = get_offender_profile(accused_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Accused not found")
    return profile
