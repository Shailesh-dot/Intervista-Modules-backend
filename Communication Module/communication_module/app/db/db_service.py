"""
db_service.py
──────────────
Helper functions to save assessment results into Supabase.
Called from endpoints/pipelines after evaluation is complete.
"""

from app.db.supabase_client import supabase


# ─────────────────────────────────────────────────────────────────────────────
# Speaking — save results
# ─────────────────────────────────────────────────────────────────────────────

def save_speaking_session(session_id: str, questions: list, aggregated: dict, interview_id: str = None):
    """
    Save the aggregated speaking session result to Supabase.
    Called after aggregate_speaking_session() returns.
    """
    try:
        print(f"[DB] Saving speaking session {session_id} for interview {interview_id}")
        summary = aggregated.get("summary", {})
        row = {
            "session_id":       session_id,
            "interview_id":     interview_id,
            "questions":        questions,
            "final_score":      aggregated.get("final_score"),
            "final_score_10":   aggregated.get("final_score_10"),
            "verdict":          summary.get("verdict", ""),
            "strengths":        summary.get("strengths", []),
            "improvements":     summary.get("improvements", []),
            "details":          aggregated.get("details", {}),
            "continuous_scores": aggregated.get("_continuous_scores", {}),
        }
        supabase.table("speaking_sessions").upsert(
            row, on_conflict="session_id"
        ).execute()
        print(f"[DB] Speaking session {session_id} saved")
    except Exception as e:
        print(f"[DB ERROR] Failed to save speaking session: {e}")


def save_speaking_clip_result(
    session_id: str,
    question_index: int,
    question_text: str,
    result: dict,
    interview_id: str = None,
):
    """
    Save a single per-question speaking evaluation result.
    Called after run_pipeline() or during evaluate_all_speaking().
    """
    try:
        print(f"[DB] Saving speaking clip Q{question_index+1} for session {session_id} (interview: {interview_id})")
        details = result.get("details", {})
        row = {
            "session_id":       session_id,
            "interview_id":     interview_id,
            "question_index":   question_index,
            "question_text":    question_text,
            "transcript":       result.get("transcript", ""),
            "final_score":      result.get("final_score"),
            "final_score_10":   result.get("final_score_10"),
            "pronunciation":    details.get("pronunciation", {}),
            "fluency":          details.get("fluency", {}),
            "tone":             details.get("tone", {}),
            "grammar":          details.get("grammar", {}),
            "comprehension":    details.get("comprehension", {}),
            "continuous_scores": result.get("_continuous_scores", {}),
            "status":           result.get("status", "evaluated"),
        }
        supabase.table("speaking_clip_results").upsert(
            row, on_conflict="session_id, question_index"
        ).execute()
        print(f"[DB] Speaking clip Q{question_index+1} for session {session_id} saved")
    except Exception as e:
        print(f"[DB ERROR] Failed to save speaking clip result: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Listening — save results
# ─────────────────────────────────────────────────────────────────────────────

def save_listening_session(session_id: str, aggregated: dict, interview_id: str = None):
    """
    Save the aggregated listening session result to Supabase.
    Called after aggregate_listening_scores() returns.
    """
    try:
        summary = aggregated.get("summary", {})
        row = {
            "session_id":       session_id,
            "interview_id":     interview_id,
            "listening_score":  aggregated.get("listening_score"),
            "listening_score_10": aggregated.get("listening_score_10"),
            "verdict":          summary.get("verdict", ""),
            "strengths":        summary.get("strengths", []),
            "improvements":     summary.get("improvements", []),
            "parameters":       aggregated.get("parameters", {}),
            "continuous_scores": aggregated.get("_continuous_scores", {}),
        }
        supabase.table("listening_sessions").upsert(
            row, on_conflict="session_id"
        ).execute()
        print(f"[DB] Listening session {session_id} saved")
    except Exception as e:
        print(f"[DB ERROR] Failed to save listening session: {e}")


def save_listening_clip_result(session_id: str, clip_result: dict, interview_id: str = None):
    """
    Save a single per-clip listening evaluation result.
    Called after evaluate_all_responses() returns.
    """
    try:
        print(f"[DB] Saving listening clip {clip_result.get('clip_id')} for session {session_id} (interview: {interview_id})")
        row = {
            "session_id":               session_id,
            "interview_id":             interview_id,
            "clip_id":                  clip_result.get("clip_id", ""),
            "task_type":                clip_result.get("task_type", ""),
            "reference_text":           clip_result.get("reference_text", ""),
            "transcript":               clip_result.get("transcript", ""),
            "listening_accuracy":       clip_result.get("listening_accuracy", {}),
            "retention":                clip_result.get("retention", {}),
            "comprehension":            clip_result.get("comprehension", {}),
            "answers":                  clip_result.get("answers", {}),
            "key_facts":                clip_result.get("key_facts", []),
        }
        supabase.table("listening_clip_results").upsert(
            row, on_conflict="session_id, clip_id"
        ).execute()
        print(f"[DB] Listening clip {clip_result.get('clip_id')} for session {session_id} saved")
    except Exception as e:
        print(f"[DB ERROR] Failed to save listening clip result: {e}")
