from fastapi import Header, HTTPException
from typing import Optional


async def get_candidate_id(x_candidate_id: Optional[str] = Header(default="anonymous")) -> str:
    """
    Extract candidate ID from request header.
    Frontend should send: X-Candidate-Id: <uuid>
    Falls back to 'anonymous' if not provided.
    """
    return x_candidate_id
