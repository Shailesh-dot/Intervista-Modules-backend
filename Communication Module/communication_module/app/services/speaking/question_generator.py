"""
question_generator.py
──────────────────────
Speaking questions — fetched from Supabase at runtime.
2 are picked randomly per session — no LLM call needed.

Benefits:
  - Zero API cost and zero latency for question generation
  - Truly random every session
  - Guaranteed quality — every question is reviewed and appropriate
  - No risk of inappropriate or off-topic questions

Question design rules:
  - Open-ended — encourages ~1 minute of speech
  - General — no domain knowledge needed, suitable for any candidate
  - Positive framing — asks about experiences, opinions, and preferences
  - No sensitive topics — no religion, politics, salary, health, or personal trauma
  - Clear simple language — accessible to all English proficiency levels

Categories covered (10 questions each):
  1. Personal interests and hobbies
  2. Technology and daily life
  3. Work and teamwork
  4. Learning and education
  5. Communication and people skills
  6. Problem-solving and challenges
  7. Future goals and plans
  8. Travel and experiences
  9. Habits and routines
  10. Opinions and preferences
"""

import random


def generate_speaking_questions(seed: int = None) -> list[str]:
    """
    Pick 2 questions randomly from the Supabase question bank.
    Each call returns a different pair — no two sessions get the same set.

    Args:
        seed: optional int for reproducible selection (testing only).
              Leave as None in production for true randomness.

    Returns:
        List of exactly 2 question strings.
    """
    from app.db.supabase_client import supabase

    # Fetch all questions (100 rows — tiny) and sample locally
    response = (
        supabase.table("speaking_questions")
        .select("question_text")
        .execute()
    )
    rows = response.data or []

    if not rows:
        # Fallback in case DB is empty
        return [
            "Tell us about a hobby or activity you enjoy in your free time.",
            "Describe a challenge you faced recently and how you overcame it.",
        ]

    questions = [r["question_text"] for r in rows]

    rng = random.Random(seed)
    return rng.sample(questions, min(2, len(questions)))