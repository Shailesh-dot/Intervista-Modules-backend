from app.services.judge0_service import run_code
from app.core.logger import logger


def execute(
    source_code: str,
    language_id: int,
    stdin: str = "",
    time_limit: int = 2,
    memory_limit: int = 128000,
) -> dict:
    """Single entry point for all code execution. Wraps judge0_service.run_code."""
    logger.info(f"Executing | lang={language_id} | stdin_len={len(stdin)}")
    result = run_code(source_code, language_id, stdin, time_limit, memory_limit)
    logger.info(f"Execution done | status={result['status']}")
    return result
