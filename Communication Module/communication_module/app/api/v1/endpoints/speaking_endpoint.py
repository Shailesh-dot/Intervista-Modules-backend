from fastapi import APIRouter, Body, UploadFile, File, Form, HTTPException
import uuid

from app.services.speaking.question_generator import generate_speaking_questions
from app.core.scoring_engine import aggregate_speaking_session
from app.core.pipeline import run_pipeline, run_session_pipeline
from app.db.db_service import save_speaking_session, save_speaking_clip_result

router = APIRouter()

# In-memory store for speaking sessions
SPEAKING_SESSION_STORE: dict[str, dict] = {}


@router.get("/speaking/questions")
async def get_speaking_questions(interview_id: str = None):
    print(f"[API] Starting speaking session. interview_id received: {interview_id}")
    """
    Starts a new speaking session.
    Returns a session_id + 3 speaking questions:
    - Q1: static ("Tell me about yourself.")
    - Q2, Q3: dynamically generated via LLM
    """
    # Generate interview_id if not provided by frontend
    if not interview_id:
        interview_id = str(uuid.uuid4())
        print(f"[API] Generated new interview_id: {interview_id}")

    dynamic = generate_speaking_questions()

    questions = [
        "Tell me about yourself.",
        dynamic[0],
        dynamic[1],
    ]
    
    session_id = str(uuid.uuid4())
    SPEAKING_SESSION_STORE[session_id] = {
        "questions": questions,
        "interview_id": interview_id
    }

    return {
        "session_id": session_id, 
        "questions": questions,
        "interview_id": interview_id
    }


@router.post("/evaluate")
async def evaluate(
    session_id: str = Form(...),
    question_index: int = Form(...),
    audio: UploadFile = File(...)
):
    """Evaluate a single clip for a session."""
    if session_id not in SPEAKING_SESSION_STORE:
        raise HTTPException(status_code=400, detail="Invalid or expired session_id")
        
    session_data = SPEAKING_SESSION_STORE[session_id]
    questions = session_data.get("questions", [])
    interview_id = session_data.get("interview_id")
    if question_index < 0 or question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question_index")

    result = await run_pipeline(audio, questions[question_index])

    # ── Save result to Supabase ───────────────────────────────────────────────
    try:
        # Ensure session exists in DB first
        save_speaking_session(session_id, questions, {
            "final_score": None, "final_score_10": None,
            "summary": {"verdict": "in_progress", "strengths": [], "improvements": []},
            "details": {},
        }, interview_id)
        save_speaking_clip_result(session_id, question_index, questions[question_index], result, interview_id)
    except Exception as e:
        print(f"[DB] Non-blocking save error: {e}")

    return result


@router.post("/speaking/evaluate_all")
async def evaluate_all_speaking(
    session_id: str = Form(...),
    audio_1: UploadFile = File(...),
    audio_2: UploadFile = File(...),
    audio_3: UploadFile = File(...),
):
    """
    Evaluate all 3 speaking questions at once using the session store.
    """
    if session_id not in SPEAKING_SESSION_STORE:
        raise HTTPException(status_code=400, detail="Invalid or expired session_id")
    
    session_data = SPEAKING_SESSION_STORE[session_id]
    questions = session_data.get("questions", [])
    interview_id = session_data.get("interview_id")

    audio_files = [
        (audio_1, questions[0]),
        (audio_2, questions[1]),
        (audio_3, questions[2]),
    ]
    results = await run_session_pipeline(audio_files)
    aggregated = aggregate_speaking_session(results)

    # ── Save all results to Supabase ──────────────────────────────────────────
    try:
        save_speaking_session(session_id, questions, aggregated, interview_id)
        for i, result in enumerate(results):
            save_speaking_clip_result(session_id, i, questions[i], result, interview_id)
    except Exception as e:
        print(f"[DB] Non-blocking save error: {e}")

    return aggregated


@router.post("/speaking/aggregate")
async def aggregate_speaking(clip_results: list = Body(...)):
    """
    Receives an array of speaking evaluation results and aggregates them
    into a single overall score and summary.
    """
    return aggregate_speaking_session(clip_results)
