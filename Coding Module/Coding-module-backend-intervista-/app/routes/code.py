from fastapi import APIRouter, HTTPException
from app.schemas.code_schema import CodeRunRequest
from app.services.execution_service import execute
from app.exceptions.custom_exceptions import Judge0Error
from app.utils.response_formatter import success_response

router = APIRouter(prefix="/code", tags=["Code Execution"])


@router.post("/run", response_model=dict, summary="Raw code run (language_id, no question context)")
def run_code(request: CodeRunRequest):
    """
    Low-level run — accepts language_id integer directly.
    Use POST /submit/run for question-aware execution with language string.
    """
    try:
        result = execute(request.source_code, request.language_id, request.stdin)
        return success_response(result)
    except Judge0Error as e:
        raise HTTPException(status_code=502, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")
