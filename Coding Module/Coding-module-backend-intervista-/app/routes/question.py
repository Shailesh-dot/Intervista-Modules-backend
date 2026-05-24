from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi_cache.decorator import cache
from app.services.question_service import (
    fetch_question_safe, fetch_all_questions_safe,
    fetch_random_question_safe, fetch_question, get_stats,
    fetch_random_question_set_safe
)
from app.services.execution.code_builder import get_boilerplate_for_language
from app.utils.languages import LANGUAGE_MAP, LANGUAGE_DISPLAY
from app.utils.response_formatter import success_response

router = APIRouter(prefix="/question", tags=["Questions"])


@router.get("/random", response_model=dict, summary="Get a random question (public)")
def get_random_question():
    """Public — no login required. Used to show candidates a question."""
    q = fetch_random_question_safe()
    if not q:
        raise HTTPException(status_code=404, detail="No questions available yet")
    return success_response(q)


@router.get("/random-set", response_model=dict, summary="Get a curated set of 3 questions (E/M/H)")
def get_random_set():
    """Returns exactly 3 random questions: 1 Easy, 1 Medium, 1 Hard (if available)."""
    qs = fetch_random_question_set_safe()
    if not qs:
        raise HTTPException(status_code=404, detail="No questions available yet")
    return success_response(qs)


@router.get("/stats", response_model=dict, summary="Question stats (public)")
@cache(expire=3600)
def question_stats():
    return success_response(get_stats())


@router.get("/languages", response_model=dict, summary="All supported languages (public)")
@cache(expire=86400)
def list_languages():
    return success_response({
        lang: {"language_id": lid, "display": LANGUAGE_DISPLAY.get(lang, lang)}
        for lang, lid in LANGUAGE_MAP.items()
    })


@router.get("/{question_id}/boilerplate", response_model=dict, summary="Get boilerplate (public envelope)")
@cache(expire=3600)
def get_boilerplate(
    question_id: str,
    language: str = Query(default="python"),
):
    """Returns the starter code."""
    q = fetch_question(question_id)
    bp = q.boilerplates.get(language, {})
    
    if isinstance(bp, dict):
        code_str = bp.get("code") or bp.get("source_code") or ""
        template_str = bp.get("template", "")
        lang_id = bp.get("language_id", LANGUAGE_MAP.get(language))
    else:
        code_str = getattr(bp, "code", getattr(bp, "source_code", ""))
        template_str = getattr(bp, "template", "")
        lang_id = getattr(bp, "language_id", LANGUAGE_MAP.get(language))

    return success_response({
        "language": language,
        "language_id": lang_id,
        "code": code_str,
        "template": template_str,
        "allowed_languages": q.allowed_languages,
    })


@router.get("/{question_id}", response_model=dict, summary="Get question by ID (public)")
@cache(expire=3600)
def get_question(question_id: str):
    """Public — returns question without hidden test cases."""
    q = fetch_question_safe(question_id)
    return success_response(q)


@router.get("/", response_model=dict, summary="List all questions (public)")
@cache(expire=300)
def list_questions():
    return success_response(fetch_all_questions_safe())
