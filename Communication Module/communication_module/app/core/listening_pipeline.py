"""
listening_pipeline.py
──────────────────────
Three operations exposed to the endpoint layer:

  generate_listening_clips()     → picks 4 random clips, TTS → base64 audio
  submit_all_responses(...)      → receives all audio, transcribes, evaluates all 4 together
  aggregate_session(clip_results) → final score + summary
"""

import base64
import uuid
import asyncio

from app.services.speech.whisper_service import transcribe_audio
from app.services.listening.listening_service import evaluate_all_responses
from app.services.listening.listening_scoring_engine import aggregate_listening_scores
from app.services.listening.content_bank import get_session_clips, ListeningClip
from app.services.tts.tts_service import synthesize_text
from app.db.db_service import save_listening_session, save_listening_clip_result


# ─────────────────────────────────────────────────────────────────────────────
# In-memory session store  {session_id → list[ListeningClip]}
# ─────────────────────────────────────────────────────────────────────────────

SESSION_STORE: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Generate clips for a session
# ─────────────────────────────────────────────────────────────────────────────

async def generate_listening_clips(interview_id: str = None) -> dict:
    print(f"[API] Starting listening session. interview_id received: {interview_id}")
    """
    Pick 2 REPEAT + 2 QnA clips randomly, synthesise audio via Azure TTS,
    return base64 audio + metadata. Creates and stores a session.
    """
    # Generate interview_id if not provided by frontend
    if not interview_id:
        interview_id = str(uuid.uuid4())
        print(f"[API] Generated new interview_id: {interview_id}")

    clips      = get_session_clips()
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "clips": clips,
        "interview_id": interview_id
    }

    output = []
    for clip in clips:
        try:
            audio_bytes = synthesize_text(clip.reference_text)
            audio_b64   = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            print(f"TTS ERROR [{clip.clip_id}]: {e}")
            audio_b64 = None

        output.append({
            "clip_id":   clip.clip_id,
            "task_type": clip.task_type,
            "audio_b64": audio_b64,
            "questions": clip.questions,
        })

    return {
        "session_id": session_id, 
        "clips": output,
        "interview_id": interview_id
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Receive and evaluate responses
# ─────────────────────────────────────────────────────────────────────────────

async def submit_all_responses(
    session_id:   str,
    clip_audios:  dict,
) -> list:
    """
    Bulk submission: Transcribe all submitted audio files, then evaluate.
    """
    session_data = SESSION_STORE.get(session_id, {})
    session_clips = session_data.get("clips")
    interview_id = session_data.get("interview_id")
    if not session_clips:
        return [{"error": "Invalid or expired session_id"}]

    clip_responses = []

    for clip in session_clips:
        cid   = clip.clip_id
        audio = clip_audios.get(cid)

        if audio is None:
            clip_responses.append({
                "clip_id": cid, "transcript": "", "whisper_segments": [], "whisper_words": []
            })
            continue

        if clip.task_type == "REPEAT":
            audio.file.seek(0)
            td = await transcribe_audio(audio)
            clip_responses.append({
                "clip_id":          cid,
                "transcript":       td.get("text", "").strip(),
                "whisper_segments": td.get("timestamps", []),
                "whisper_words":    td.get("words", []),
            })
        elif clip.task_type == "QnA":
            audio_q1 = audio.get("q1") if isinstance(audio, dict) else audio

            td1 = {"text": "", "timestamps": [], "words": []}

            if audio_q1:
                audio_q1.file.seek(0)
                td1 = await transcribe_audio(audio_q1)

            clip_responses.append({
                "clip_id":    cid,
                "answer_q1":  td1.get("text", "").strip(),
                "segments_q1": td1.get("timestamps", []),
                "words_q1":    td1.get("words", []),
            })

    results = await asyncio.to_thread(evaluate_all_responses, session_clips, clip_responses)

    # ── Aggregate and Save to Supabase ────────────────────────────────────────
    try:
        # Immediate aggregation for batch submission
        aggregated = aggregate_listening_scores(results)
        
        # Save session with actual scores instead of placeholders
        save_listening_session(session_id, aggregated, interview_id)
        
        # Save individual clips
        for clip_result in results:
            save_listening_clip_result(session_id, clip_result, interview_id)
            
        print(f"[{session_id}] Batch submission evaluated and saved to DB.")
    except Exception as e:
        print(f"[DB] Non-blocking save error: {e}")

    return results


async def evaluate_clip_response(
    session_id: str,
    clip_id: str,
    audio_file,
    question_index: int = 0,
) -> dict:
    """
    Legacy evaluator (one-by-one) for the current frontend/endpoint.
    """
    session_data = SESSION_STORE.get(session_id, {})
    session_clips = session_data.get("clips")
    interview_id = session_data.get("interview_id")
    if not session_clips: return {"error": "Invalid session_id"}

    clip = next((c for c in session_clips if c.clip_id == clip_id), None)
    if not clip: return {"error": "Invalid clip_id"}

    audio_file.file.seek(0)
    td = await transcribe_audio(audio_file)

    responses = []
    if clip.task_type == "REPEAT":
        responses.append({
            "clip_id": clip_id if 'clip_id' in locals() else clip_id,
            "transcript": td.get("text", "").strip(),
            "whisper_segments": td.get("timestamps", []),
            "whisper_words": td.get("words", []),
        })
        responses.append({
            "clip_id": clip_id,
            "answer_q1": td.get("text", "").strip(),
            "segments_q1": td.get("timestamps", []),
            "words_q1": td.get("words", []),
        })

    results = await asyncio.to_thread(evaluate_all_responses, session_clips, responses)
    result = next((r for r in results if r["clip_id"] == clip_id), {"error": "Evaluation failed"})
    
    # ── Save clip result to Supabase ─────────────────────────────────────────
    if "error" not in result:
        try:
            # Ensure session exists in DB (placeholder scores until aggregation)
            save_listening_session(session_id, {
                "listening_score": None, "listening_score_10": None,
                "summary": {"verdict": "in_progress", "strengths": [], "improvements": []},
                "parameters": {},
            }, interview_id)
            save_listening_clip_result(session_id, result, interview_id)
        except Exception as e:
            print(f"[DB] Non-blocking save error: {e}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Aggregate final score
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_session(clip_results: list, session_id: str = None) -> dict:
    result = aggregate_listening_scores(clip_results)

    # ── Update session with final aggregated scores ───────────────────────────
    if session_id:
        try:
            # Retrieve interview_id if available
            session_data = SESSION_STORE.get(session_id, {})
            interview_id = session_data.get("interview_id")
            save_listening_session(session_id, result, interview_id)
        except Exception as e:
            print(f"[DB] Non-blocking save error: {e}")

    return result