"""
init_tables.py
───────────────
Creates all 6 Supabase tables for the communication module.
Idempotent — uses CREATE TABLE IF NOT EXISTS.

Run: python -m scripts.init_tables
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.supabase_client import supabase

SQL_STATEMENTS = [

    # ── 1. Listening clips (question bank) ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS listening_clips (
        id          BIGSERIAL PRIMARY KEY,
        clip_id     TEXT UNIQUE NOT NULL,
        task_type   TEXT NOT NULL CHECK (task_type IN ('REPEAT', 'QnA')),
        reference_text TEXT NOT NULL,
        questions   JSONB DEFAULT '[]'::jsonb,
        key_facts   JSONB DEFAULT '[]'::jsonb,
        created_at  TIMESTAMPTZ DEFAULT now()
    );
    """,

    # ── 2. Speaking questions (question bank) ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS speaking_questions (
        id              BIGSERIAL PRIMARY KEY,
        question_text   TEXT UNIQUE NOT NULL,
        category        TEXT DEFAULT 'general',
        created_at      TIMESTAMPTZ DEFAULT now()
    );
    """,

    # ── 3. Speaking sessions ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS speaking_sessions (
        id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id      TEXT UNIQUE NOT NULL,
        questions       JSONB DEFAULT '[]'::jsonb,
        final_score     DOUBLE PRECISION,
        final_score_10  INTEGER,
        verdict         TEXT,
        strengths       JSONB DEFAULT '[]'::jsonb,
        improvements    JSONB DEFAULT '[]'::jsonb,
        details         JSONB DEFAULT '{}'::jsonb,
        continuous_scores JSONB DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ DEFAULT now()
    );
    """,

    # ── 4. Speaking clip results (per-question) ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS speaking_clip_results (
        id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id      TEXT NOT NULL REFERENCES speaking_sessions(session_id),
        question_index  INTEGER NOT NULL,
        question_text   TEXT,
        transcript      TEXT,
        final_score     DOUBLE PRECISION,
        final_score_10  INTEGER,
        pronunciation   JSONB DEFAULT '{}'::jsonb,
        fluency         JSONB DEFAULT '{}'::jsonb,
        tone            JSONB DEFAULT '{}'::jsonb,
        grammar         JSONB DEFAULT '{}'::jsonb,
        comprehension   JSONB DEFAULT '{}'::jsonb,
        continuous_scores JSONB DEFAULT '{}'::jsonb,
        status          TEXT DEFAULT 'evaluated',
        created_at      TIMESTAMPTZ DEFAULT now()
    );
    """,

    # ── 5. Listening sessions ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS listening_sessions (
        id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id          TEXT UNIQUE NOT NULL,
        listening_score     DOUBLE PRECISION,
        listening_score_10  INTEGER,
        verdict             TEXT,
        strengths           JSONB DEFAULT '[]'::jsonb,
        improvements        JSONB DEFAULT '[]'::jsonb,
        parameters          JSONB DEFAULT '{}'::jsonb,
        continuous_scores   JSONB DEFAULT '{}'::jsonb,
        created_at          TIMESTAMPTZ DEFAULT now()
    );
    """,

    # ── 6. Listening clip results (per-clip) ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS listening_clip_results (
        id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id              TEXT NOT NULL REFERENCES listening_sessions(session_id),
        clip_id                 TEXT NOT NULL,
        task_type               TEXT,
        reference_text          TEXT,
        transcript              TEXT,
        listening_accuracy      JSONB DEFAULT '{}'::jsonb,
        retention               JSONB DEFAULT '{}'::jsonb,
        sentence_reconstruction JSONB DEFAULT '{}'::jsonb,
        answers                 JSONB DEFAULT '{}'::jsonb,
        key_facts               JSONB DEFAULT '[]'::jsonb,
        created_at              TIMESTAMPTZ DEFAULT now()
    );
    """,
]


def init_tables():
    print("Creating tables in Supabase...")
    for i, sql in enumerate(SQL_STATEMENTS, 1):
        try:
            supabase.rpc("exec_sql", {"query": sql.strip()}).execute()
            print(f"  ✓ Table {i}/6 created")
        except Exception as e:
            # Fallback: try postgrest-py raw SQL via the REST endpoint
            print(f"  ⚠ RPC failed for table {i}, trying direct SQL: {e}")
            try:
                supabase.postgrest.schema("public").rpc("exec_sql", {"query": sql.strip()}).execute()
            except Exception as e2:
                print(f"  ✗ Table {i} failed: {e2}")
                print(f"    → You may need to run this SQL manually in the Supabase SQL Editor.")
                print(f"    SQL:\n{sql.strip()}\n")

    print("\nDone! All tables should now exist in your Supabase project.")


if __name__ == "__main__":
    init_tables()
