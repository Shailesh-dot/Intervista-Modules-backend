from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from app.schemas.submission_schema import SubmissionRequest, RunRequest, SubmissionEnqueueResponse, SubmissionStatusResponse
from app.utils.limiter import limiter
from app.services.submission_service import (
    run_code_request, enqueue_submission, process_submission_worker,
    get_submission_by_id, get_candidate_history,
    get_question_submissions, get_all_submissions,
)
from app.auth.dependencies import admin_required
from app.utils.response_formatter import success_response

router = APIRouter(prefix="/submit", tags=["Submissions"])


@router.post("/run", response_model=dict, summary="Run code directly (public)")
@limiter.limit("5/minute")
def run_code(request: Request, body: RunRequest):
    """Run button — execute code with custom stdin."""
    result = run_code_request(body)
    return success_response(result)


@router.post("/", response_model=dict, summary="Submit code async (public envelope)")
@limiter.limit("5/minute")
def submit(request: Request, body: SubmissionRequest, background_tasks: BackgroundTasks):
    """
    Submit button — immediately returns 'queued' status.
    Uses BackgroundTasks to process against Batch Judge0 API natively.
    """
    if body.session_id:
        from app.storage.assessment_store import get_session, complete_session
        from datetime import datetime, timezone
        session_obj = get_session(body.session_id)
        if not session_obj:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session_obj.status != "active":
            raise HTTPException(status_code=400, detail=f"Session is {session_obj.status}")
        if datetime.now(timezone.utc) > session_obj.end_time:
            complete_session(body.session_id, "expired")
            raise HTTPException(status_code=400, detail="Assessment time expired")
            
    submission_id, question, language_id = enqueue_submission(body)
    
    background_tasks.add_task(
        process_submission_worker,
        submission_id=submission_id,
        question=question,
        source_code=body.source_code,
        language_id=language_id
    )
    
    response_data = SubmissionEnqueueResponse(submission_id=submission_id, status="processing")
    return success_response(response_data.model_dump(), message="Submission placed in queue.")


@router.get("/{submission_id}/status", response_model=dict, summary="Poll submission status")
def get_submission_status(submission_id: str):
    """Used by frontend to poll for asynchronous execution completion."""
    try:
        result = get_submission_by_id(submission_id)
        return success_response(result.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/all", response_model=dict, summary="All submissions (admin only)")
def list_all(_=Depends(admin_required)):
    return success_response([s.model_dump() for s in get_all_submissions()])


@router.get("/candidate/{candidate_id}", response_model=dict, summary="Candidate history")
def candidate_submissions(candidate_id: str):
    return success_response([r.model_dump() for r in get_candidate_history(candidate_id)])


@router.get("/question/{question_id}", response_model=dict, summary="Submissions for a question")
def question_submissions(question_id: str, _=Depends(admin_required)):
    return success_response([r.model_dump() for r in get_question_submissions(question_id)])


@router.get("/{submission_id}", response_model=dict, summary="Legacy Get submission by ID")
def get_submission(submission_id: str):
    """Same as /status, retained for legacy compatibility."""
    return get_submission_status(submission_id)
