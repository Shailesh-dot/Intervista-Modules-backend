"""
Auth Dependencies
-----------------
FastAPI dependency functions injected into route handlers.

Usage:
    @router.post("/admin/question")
    def create_question(data: ..., _=Depends(admin_required)):
        ...
"""

from fastapi import Depends, HTTPException, status, Header
from app.config import ADMIN_SECRET_KEY

def admin_required(x_admin_key: str = Header(default=None)):
    """
    Dependency that restricts access to admin users only via API key.
    Raises 403 if the provided API key is invalid.
    """
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required (Invalid X-Admin-Key)",
        )

