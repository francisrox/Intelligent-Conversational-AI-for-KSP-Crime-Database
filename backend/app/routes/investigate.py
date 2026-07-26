from fastapi import APIRouter, Depends, HTTPException

from app.services.case_intelligence import generate_case_summary, find_similar_cases
from app.services.auth import get_current_user, log_audit

router = APIRouter()


@router.get("/case/{crime_id}")
def investigate_case(crime_id: int, user: dict = Depends(get_current_user)):
    """Auto-summary + investigative leads + similar past cases for one FIR.
    Requires being logged in (any role) — demonstrates Module 10 protecting
    a real Module 6 feature, not just a standalone auth demo."""
    result = generate_case_summary(crime_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Case not found")

    similar = find_similar_cases(crime_id)
    log_audit(user, "view_case_investigation", f"/api/investigate/case/{crime_id}")

    return {**result, "similar_cases": similar}
