from fastapi import APIRouter
import requests
from app.config import JUDGE0_URL
from app.storage.question_store import count_questions
from app.storage.submission_store import count_submissions
from app.storage.user_store import count_users
from app.core.logger import logger

router = APIRouter(tags=["Health"])


@router.get("/health", summary="API health check")
def health():
    return {
        "status": "ok",
        "service": "Coding Assessment API v6",
        "questions_loaded": count_questions(),
        "submissions_stored": count_submissions(),
        "users_registered": count_users(),
    }


@router.get("/health/judge0", summary="Judge0 connectivity check")
def judge0_health():
    try:
        resp = requests.get(f"{JUDGE0_URL}/statuses", timeout=5)
        if resp.status_code == 200:
            return {"status": "ok", "judge0_url": JUDGE0_URL}
        return {"status": "degraded", "judge0_url": JUDGE0_URL, "http_status": resp.status_code}
    except Exception as e:
        logger.error(f"Judge0 unreachable: {e}")
        return {"status": "unreachable", "judge0_url": JUDGE0_URL, "detail": str(e)}
