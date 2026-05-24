-- ============================================================================
-- Supabase SQL — Run this in the Supabase SQL Editor (https://supabase.com/dashboard)
-- Creates all 6 tables for the Communication Assessment Module
-- ============================================================================

-- 1. Listening clips (question bank)
CREATE TABLE IF NOT EXISTS listening_clips (
    id              BIGSERIAL PRIMARY KEY,
    clip_id         TEXT UNIQUE NOT NULL,
    task_type       TEXT NOT NULL CHECK (task_type IN ('REPEAT', 'QnA')),
    reference_text  TEXT NOT NULL,
    questions       JSONB DEFAULT '[]'::jsonb,
    key_facts       JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2. Speaking questions (question bank)
CREATE TABLE IF NOT EXISTS speaking_questions (
    id              BIGSERIAL PRIMARY KEY,
    question_text   TEXT UNIQUE NOT NULL,
    category        TEXT DEFAULT 'general',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 3. Speaking sessions (session-level aggregated results)
CREATE TABLE IF NOT EXISTS speaking_sessions (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id          TEXT UNIQUE NOT NULL,
    questions           JSONB DEFAULT '[]'::jsonb,
    final_score         DOUBLE PRECISION,
    final_score_10      INTEGER,
    verdict             TEXT,
    strengths           JSONB DEFAULT '[]'::jsonb,
    improvements        JSONB DEFAULT '[]'::jsonb,
    details             JSONB DEFAULT '{}'::jsonb,
    continuous_scores   JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- 4. Speaking clip results (per-question evaluation)
CREATE TABLE IF NOT EXISTS speaking_clip_results (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id          TEXT NOT NULL REFERENCES speaking_sessions(session_id),
    question_index      INTEGER NOT NULL,
    question_text       TEXT,
    transcript          TEXT,
    final_score         DOUBLE PRECISION,
    final_score_10      INTEGER,
    pronunciation       JSONB DEFAULT '{}'::jsonb,
    fluency             JSONB DEFAULT '{}'::jsonb,
    tone                JSONB DEFAULT '{}'::jsonb,
    grammar             JSONB DEFAULT '{}'::jsonb,
    comprehension       JSONB DEFAULT '{}'::jsonb,
    continuous_scores   JSONB DEFAULT '{}'::jsonb,
    status              TEXT DEFAULT 'evaluated',
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (session_id, question_index)
);

-- 5. Listening sessions (session-level aggregated results)
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

-- 6. Listening clip results (per-clip evaluation)
CREATE TABLE IF NOT EXISTS listening_clip_results (
    id                          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id                  TEXT NOT NULL REFERENCES listening_sessions(session_id),
    clip_id                     TEXT NOT NULL,
    task_type                   TEXT,
    reference_text              TEXT,
    transcript                  TEXT,
    listening_accuracy          JSONB DEFAULT '{}'::jsonb,
    retention                   JSONB DEFAULT '{}'::jsonb,
    sentence_reconstruction     JSONB DEFAULT '{}'::jsonb,
    answers                     JSONB DEFAULT '{}'::jsonb,
    key_facts                   JSONB DEFAULT '[]'::jsonb,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (session_id, clip_id)
);
