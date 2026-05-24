from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.logger import logger


async def custom_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "Bad request", "detail": str(exc)},
    )
