from typing import List, Optional
from app.schemas.question_schema import QuestionResponse, QuestionAdminResponse
from app.storage.question_store import (
    get_question, get_question_safe, list_questions, get_random_question, 
    count_questions, get_random_question_set_by_difficulty
)
from app.exceptions.custom_exceptions import QuestionNotFoundError
from app.core.logger import logger

def fetch_question(question_id: str) -> QuestionAdminResponse:
    """Full Question object — used internally (includes hidden TCs)."""
    q = get_question(question_id)
    if not q:
        raise QuestionNotFoundError(question_id)
    return q

def fetch_question_safe(question_id: str) -> dict:
    """Question without hidden_test_cases — for candidate frontend."""
    q = get_question_safe(question_id)
    if not q:
        raise QuestionNotFoundError(question_id)
    return q.model_dump()

def fetch_all_questions_safe() -> List[dict]:
    return [q.model_dump() for q in list_questions()]

def fetch_random_question_safe() -> Optional[dict]:
    q = get_random_question()
    return q.model_dump() if q else None

def fetch_random_question_set_safe() -> List[dict]:
    qs = get_random_question_set_by_difficulty()
    return [q.model_dump() for q in qs]

def get_stats() -> dict:
    questions = list_questions()
    by_difficulty = {"Easy": 0, "Medium": 0, "Hard": 0}
    for q in questions:
        if q.difficulty in by_difficulty:
            by_difficulty[q.difficulty] += 1
    return {
        "total_questions": count_questions(),
        "by_difficulty": by_difficulty,
    }
