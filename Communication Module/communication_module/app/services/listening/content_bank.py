"""
content_bank.py
───────────────
Listening clip data — fetched from Supabase at runtime.

Audio is synthesised once via Azure TTS and served per session.

Layout:
  REPEAT clips — candidate repeats the sentence verbatim
  QnA clips    — candidate answers questions about the passage

Per session: 2 REPEAT + 2 QnA selected randomly → different every time.

Each clip carries key_facts used by the accuracy scorer as a ground-truth
signal (keyword matching), making scoring more deterministic and faster.
"""

import random
from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class ListeningClip:
    clip_id:        str
    task_type:      str            # "REPEAT" or "QnA"
    reference_text: str
    questions:      list = field(default_factory=list)   # QnA only — 2 questions
    key_facts:      list = field(default_factory=list)
    # For REPEAT: flat list of must-appear keywords
    # For QnA:   list of lists — key_facts[0] for Q1, key_facts[1] for Q2


def _row_to_clip(row: dict) -> ListeningClip:
    """Convert a Supabase row dict → ListeningClip dataclass."""
    return ListeningClip(
        clip_id=row["clip_id"],
        task_type=row["task_type"],
        reference_text=row["reference_text"],
        questions=row.get("questions", []),
        key_facts=row.get("key_facts", []),
    )


def _fetch_random_clips(task_type: str, count: int) -> list[ListeningClip]:
    """
    Fetch `count` random clips of given task_type from Supabase.
    Uses PostgreSQL's random() for server-side random selection.
    """
    from app.db.supabase_client import supabase

    # Fetch all clips of this type, order randomly, take `count`
    # Supabase doesn't support ORDER BY random() directly via the client,
    # so we fetch all and sample locally (100 rows is tiny).
    response = (
        supabase.table("listening_clips")
        .select("*")
        .eq("task_type", task_type)
        .execute()
    )
    rows = response.data or []
    if len(rows) <= count:
        return [_row_to_clip(r) for r in rows]

    sampled = random.sample(rows, count)
    return [_row_to_clip(r) for r in sampled]


# ─────────────────────────────────────────────────────────────────────────────
# Session selector — called once per test session
# ─────────────────────────────────────────────────────────────────────────────

def get_session_clips(seed: int = None) -> list[ListeningClip]:
    """
    Pick 4 QnA clips randomly for this session.
    Returns them as clip_1..clip_4 (sequential IDs for the session).
    Each call gives a different combination without repetition.
    """
    if seed is not None:
        random.seed(seed)

    qna_clips = _fetch_random_clips("QnA", 4)
    picks     = qna_clips

    session = []
    for i, clip in enumerate(picks, start=1):
        c = deepcopy(clip)
        c.clip_id = f"clip_{i}"
        session.append(c)

    return session