from fastapi import APIRouter, Depends
from app.schemas.admin_schema import (
    QuestionCreateRequest, BulkQuestionUploadRequest, QuestionUpdateRequest,
)
from app.services.admin_service import (
    create_question, bulk_create_questions,
    update_question_by_id, delete_question_by_id, list_all_questions_admin,
)
from app.auth.dependencies import admin_required
from app.utils.response_formatter import success_response

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/question", response_model=dict, summary="Create a question (admin only)")
def admin_create_question(data: QuestionCreateRequest, _=Depends(admin_required)):
    question = create_question(data)
    return success_response(question.model_dump(), message="Question created successfully")


@router.post("/question/bulk", response_model=dict, summary="Bulk upload questions (admin only)")
def admin_bulk_upload(request: BulkQuestionUploadRequest, _=Depends(admin_required)):
    summary = bulk_create_questions(request.questions)
    return success_response(summary, message="Bulk upload complete")


@router.get("/questions", response_model=dict, summary="List all questions with hidden TCs (admin only)")
def admin_list_questions(_=Depends(admin_required)):
    questions = list_all_questions_admin()
    return success_response([q.model_dump() for q in questions])


@router.put("/question/{question_id}", response_model=dict, summary="Update a question (admin only)")
def admin_update_question(question_id: str, data: QuestionUpdateRequest, _=Depends(admin_required)):
    updated = update_question_by_id(question_id, data)
    return success_response(updated.model_dump(), message="Question updated")


@router.delete("/question/{question_id}", response_model=dict, summary="Delete a question (admin only)")
def admin_delete_question(question_id: str, _=Depends(admin_required)):
    result = delete_question_by_id(question_id)
    return success_response(result, message="Question deleted")
