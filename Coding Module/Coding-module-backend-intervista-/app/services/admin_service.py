from typing import List
from app.schemas.admin_schema import QuestionCreateRequest, QuestionUpdateRequest, BoilerplateInput
from app.schemas.question_schema import QuestionCreate, TestCaseBase, QuestionAdminResponse
from app.storage.question_store import (
    add_question, get_question, update_question,
    delete_question, list_questions_admin, question_exists,
)
from app.utils.languages import get_language_id, LANGUAGE_MAP
from app.utils.id_generator import generate_short_id
from app.exceptions.custom_exceptions import QuestionNotFoundError, DuplicateQuestionError
from app.core.logger import logger


def _resolve_boilerplates(raw: dict) -> dict:
    """
    Convert admin BoilerplateInput dict → flat dictionary.
    Auto-fills language_id from LANGUAGE_MAP if admin didn't provide it.
    """
    resolved = {}
    for lang, bp in raw.items():
        lang_id = bp.language_id or get_language_id(lang)
        if lang_id is None:
            logger.warning(f"Unknown language '{lang}' in boilerplates — skipping")
            continue
        
        mapped = {
            "template": bp.template,
            "language_id": lang_id,
        }
        if getattr(bp, "code", None) is not None:
            mapped["code"] = bp.code
        elif getattr(bp, "source_code", None) is not None:
            mapped["source_code"] = bp.source_code
            
        resolved[lang] = mapped
    return resolved


def create_question(data: QuestionCreateRequest) -> QuestionAdminResponse:
    question_id = data.id or generate_short_id(prefix="q_")

    if question_exists(question_id):
        raise DuplicateQuestionError(question_id)

    boilerplates = _resolve_boilerplates(data.boilerplates or {})

    # allowed_languages: merge from boilerplates keys + explicit list
    allowed = list(set(list(boilerplates.keys()) + (data.allowed_languages or ["python"])))

    question_data = QuestionCreate(
        id=question_id,
        title=data.title,
        description=data.description,
        difficulty=data.difficulty,
        examples=data.examples or [],
        constraints=data.constraints or [],
        sample_test_cases=[tc.model_dump() for tc in data.sample_test_cases],
        hidden_test_cases=[tc.model_dump() for tc in data.hidden_test_cases],
        boilerplates=boilerplates,
        allowed_languages=allowed,
    )

    question = add_question(question_data)
    logger.info(f"Question created: id={question_id} | title='{data.title}' | langs={allowed}")
    return question


def bulk_create_questions(questions_data: List[QuestionCreateRequest]) -> dict:
    created, skipped = [], []
    for data in questions_data:
        try:
            q = create_question(data)
            created.append(q.id)
        except DuplicateQuestionError as e:
            logger.warning(f"Skipping duplicate: {e}")
            skipped.append(data.id or "unknown")
    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created_ids": created,
        "skipped_ids": skipped,
    }


def update_question_by_id(question_id: str, data: QuestionUpdateRequest) -> QuestionAdminResponse:
    updates = data.model_dump(exclude_unset=True)

    for field in ("sample_test_cases", "hidden_test_cases"):
        if field in updates:
            updates[field] = [
                {"input": tc["input"], "expected_output": tc["expected_output"]}
                for tc in updates[field]
            ]

    if "boilerplates" in updates:
        resolved = {}
        for lang, bp_data in updates["boilerplates"].items():
            lang_id = bp_data.get("language_id") or get_language_id(lang)
            if lang_id:
                mapped = {
                    "template": bp_data["template"],
                    "language_id": lang_id,
                }
                if "code" in bp_data and bp_data["code"] is not None:
                    mapped["code"] = bp_data["code"]
                elif "source_code" in bp_data and bp_data["source_code"] is not None:
                    mapped["source_code"] = bp_data["source_code"]
                resolved[lang] = mapped
        updates["boilerplates"] = resolved

    updated = update_question(question_id, updates)
    if not updated:
        raise QuestionNotFoundError(question_id)
    logger.info(f"Question updated: id={question_id}")
    return updated


def delete_question_by_id(question_id: str) -> dict:
    if not question_exists(question_id):
        raise QuestionNotFoundError(question_id)
    delete_question(question_id)
    logger.info(f"Question deleted: id={question_id}")
    return {"deleted": True, "question_id": question_id}


def list_all_questions_admin():
    return list_questions_admin()
