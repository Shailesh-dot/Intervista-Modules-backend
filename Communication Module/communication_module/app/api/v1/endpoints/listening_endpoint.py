"""
listening_endpoint.py
──────────────────────
3 endpoints:

  GET  /api/v1/listening/clips
       → Returns session_id + 4 clips with base64 audio

  POST /api/v1/listening/respond
       → Receives all audio files for all clips in one request
       → Transcribes + evaluates all 4 together → returns clip_results

  POST /api/v1/listening/aggregate
       → Receives clip_results → returns final score + summary
"""

from fastapi import APIRouter, UploadFile, File, Form, Body
from app.core.listening_pipeline import (
    generate_listening_clips,
    submit_all_responses,
    evaluate_clip_response,
    aggregate_session,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 1 — Get clips
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/clips")
async def get_clips(interview_id: str = None):
    """
    Start a new listening session.
    Returns 4 random clips (QnA) with TTS audio as base64.

    Response:
    {
      "session_id": "uuid",
      "clips": [
        {"clip_id": "clip_1", "task_type": "QnA", "audio_b64": "...", "questions": ["Q1?","Q2?"]},
        {"clip_id": "clip_2", "task_type": "QnA", "audio_b64": "...", "questions": ["Q1?","Q2?"]},
        {"clip_id": "clip_3", "task_type": "QnA", "audio_b64": "...", "questions": ["Q1?","Q2?"]},
        {"clip_id": "clip_4", "task_type": "QnA", "audio_b64": "...", "questions": ["Q1?","Q2?"]}
      ]
    }
    """
    return await generate_listening_clips(interview_id)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 2 — Submit all responses
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/respond")
async def respond(
    session_id:     str        = Form(...),
    clip_id:        str        = Form(...),
    question_index: int        = Form(0),
    audio:          UploadFile = File(...),
):
    """
    Submit a single audio response for one clip.
    Takes one audio file.
    """
    return await evaluate_clip_response(
        session_id=session_id,
        clip_id=clip_id,
        audio_file=audio,
        question_index=question_index
    )

@router.post("/respond_all")
async def respond_all(
    session_id:  str        = Form(...),
    # 4 QnA clips — one audio file each
    clip_1_q1:   UploadFile = File(None),
    clip_2_q1:   UploadFile = File(None),
    clip_3_q1:   UploadFile = File(None),
    clip_4_q1:   UploadFile = File(None),
):
    """
    Submit all candidate audio responses in one request.

    Form fields:
      session_id   : from /clips response
      clip_1_q1    : audio answering question for QnA clip 1
      clip_2_q1    : audio answering question for QnA clip 2
      clip_3_q1    : audio answering question for QnA clip 3
      clip_4_q1    : audio answering question for QnA clip 4

    All clips are transcribed and evaluated together.

    Response: list of 4 per-clip result dicts.
    """
    clip_audios = {
        "clip_1": {"q1": clip_1_q1},
        "clip_2": {"q1": clip_2_q1},
        "clip_3": {"q1": clip_3_q1},
        "clip_4": {"q1": clip_4_q1},
    }

    clip_results = await submit_all_responses(session_id, clip_audios)
    return {"session_id": session_id, "clip_results": clip_results}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 3 — Aggregate final score
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/aggregate")
async def aggregate(
    clip_results: list = Body(...),
    session_id: str = None, # Passed as optional query param
):
    """
    Compute the final listening score from all 4 clip results.

    Body: the clip_results list returned by /respond

    Response:
    {
      "listening_score":    float,   # 0-2 weighted
      "listening_score_10": int,     # 0-10
      "summary": {
        "verdict": str,
        "strengths": [...],
        "improvements": [...]
      },
      "parameters": { ... }
    }
    """
    return aggregate_session(clip_results, session_id=session_id)