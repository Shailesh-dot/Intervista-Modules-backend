from fastapi import APIRouter, HTTPException, Depends
from app.schemas.assessment_schema import AssessmentSessionCreate, AssessmentSessionResponse
from app.storage.assessment_store import create_session, get_session, complete_session
from app.auth.dependencies import admin_required
from app.utils.response_formatter import success_response

router = APIRouter(prefix="/assessment", tags=["Assessment Sessions"])

@router.post("/start", response_model=dict, summary="Start an Interview Assessment Session")
def start_assessment(request: AssessmentSessionCreate, _=Depends(admin_required)):
    """
    Called by the main AI Interview Platform when a candidate reaches the Coding Module.
    Creates a time-bound session that expires after X minutes.
    """
    session = create_session(request.candidate_id, request.duration_minutes)
    response_data = AssessmentSessionResponse.model_validate(session)
    return success_response(response_data.model_dump(), message="Assessment session started.")

@router.get("/{session_id}", response_model=dict, summary="Get Session Details")
def fetch_session(session_id: str):
    """Retrieve time remaining and status."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return success_response(AssessmentSessionResponse.model_validate(session).model_dump())

@router.post("/{session_id}/complete", response_model=dict, summary="Complete Session early")
def finish_assessment(session_id: str):
    """Candidate clicks Finish, freezing the session permanently."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    complete_session(session_id, "completed")
    return success_response({"session_id": session_id, "status": "completed"})
