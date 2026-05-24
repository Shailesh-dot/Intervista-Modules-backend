"""
seed_questions.py
──────────────────
Seeds all 100 listening clips + 100 speaking questions into Supabase.

Run: python -m scripts.seed_questions
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.supabase_client import supabase
from scripts.seed_data import ALL_CLIPS, SPEAKING_QUESTIONS


def seed_listening_clips():
    """Insert all QnA clips into listening_clips table."""
    all_clips = ALL_CLIPS
    print(f"Seeding {len(all_clips)} listening clips...")

    for i in range(0, len(all_clips), 50):
        batch = all_clips[i:i+50]
        try:
            supabase.table("listening_clips").upsert(
                batch, on_conflict="clip_id"
            ).execute()
            print(f"  [OK] Batch {i//50 + 1}: {len(batch)} clips upserted")
        except Exception as e:
            print(f"  [FAIL] Batch {i//50 + 1} failed: {e}")

    print(f"  Done - {len(all_clips)} listening clips seeded.\n")


def seed_speaking_questions():
    """Insert all 100 speaking questions into speaking_questions table."""
    rows = [
        {"question_text": q, "category": cat}
        for q, cat in SPEAKING_QUESTIONS
    ]
    print(f"Seeding {len(rows)} speaking questions...")

    for i in range(0, len(rows), 50):
        batch = rows[i:i+50]
        try:
            supabase.table("speaking_questions").upsert(
                batch, on_conflict="question_text"
            ).execute()
            print(f"  [OK] Batch {i//50 + 1}: {len(batch)} questions upserted")
        except Exception as e:
            print(f"  [FAIL] Batch {i//50 + 1} failed: {e}")

    print(f"  Done - {len(rows)} speaking questions seeded.\n")


def verify():
    """Quick count check."""
    lc = supabase.table("listening_clips").select("id", count="exact").execute()
    sq = supabase.table("speaking_questions").select("id", count="exact").execute()
    print(f"Verification:")
    print(f"  listening_clips:    {lc.count} rows")
    print(f"  speaking_questions: {sq.count} rows")


if __name__ == "__main__":
    seed_listening_clips()
    seed_speaking_questions()
    verify()
    print("\n[OK] Seeding complete!")
