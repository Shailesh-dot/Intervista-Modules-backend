from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions.custom_exceptions import (
    QuestionNotFoundError,
    SubmissionError,
    Judge0Error,
    DuplicateQuestionError,
    InvalidInputError,
)
from app.core.logger import logger


async def question_not_found_handler(request: Request, exc: QuestionNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": str(exc)},
    )


async def duplicate_question_handler(request: Request, exc: DuplicateQuestionError):
    return JSONResponse(
        status_code=409,
        content={"success": False, "error": str(exc)},
    )


async def submission_error_handler(request: Request, exc: SubmissionError):
    logger.error(f"SubmissionError: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": f"Submission failed: {str(exc)}"},
    )


async def judge0_error_handler(request: Request, exc: Judge0Error):
    logger.error(f"Judge0Error: {exc}")
    return JSONResponse(
        status_code=502,
        content={"success": False, "error": f"Code execution engine error: {str(exc)}"},
    )


async def invalid_input_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": str(exc)},
    )


async def timeout_error_handler(request: Request, exc: TimeoutError):
    return JSONResponse(
        status_code=504,
        content={"success": False, "error": "Execution timed out. Check Judge0."},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


def register_handlers(app):
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(QuestionNotFoundError, question_not_found_handler)
    app.add_exception_handler(DuplicateQuestionError, duplicate_question_handler)
    app.add_exception_handler(SubmissionError, submission_error_handler)
    app.add_exception_handler(Judge0Error, judge0_error_handler)
    app.add_exception_handler(InvalidInputError, invalid_input_handler)
    app.add_exception_handler(TimeoutError, timeout_error_handler)
    app.add_exception_handler(Exception, global_exception_handler)
