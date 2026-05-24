from typing import Any, Optional


def success_response(data: Any, message: str = "Success") -> dict:
    """Standard success envelope used across all routes."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(error: str, detail: Optional[str] = None) -> dict:
    """Standard error envelope."""
    resp = {"success": False, "error": error}
    if detail:
        resp["detail"] = detail
    return resp


def paginated_response(data: list, total: int, page: int = 1, page_size: int = 20) -> dict:
    """Paginated list response — ready for when you add DB pagination."""
    return {
        "success": True,
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
