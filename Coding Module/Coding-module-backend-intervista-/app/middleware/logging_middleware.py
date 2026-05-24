import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request and outgoing response with:
    - HTTP method + path
    - Status code
    - Time taken in ms
    """

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        method = request.method
        path = request.url.path

        logger.info(f"→ {method} {path}")

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = int((time.time() - start) * 1000)
            logger.error(f"✗ {method} {path} — EXCEPTION after {elapsed}ms: {exc}")
            raise

        elapsed = int((time.time() - start) * 1000)
        status = response.status_code
        level = logger.warning if status >= 400 else logger.info
        level(f"← {method} {path} {status} ({elapsed}ms)")

        return response
