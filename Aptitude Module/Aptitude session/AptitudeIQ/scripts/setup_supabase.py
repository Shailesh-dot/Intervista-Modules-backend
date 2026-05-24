"""
AptitudeIQ -- Supabase Schema Setup Script
==========================================
Creates all aptitude module tables in Supabase PostgreSQL:
  1. aptitude_questions   (master table)
  2. quiz_results         (quiz summary)
  3. quiz_answers         (per-answer detail)
  4. 30 individual topic tables

Then loads all questions from data/all_questions.json into the DB.

Usage:
    python scripts/setup_supabase.py
    python scripts/setup_supabase.py --reset   # drop & recreate all tables
"""

import sys
import json
import psycopg2
from pathlib import Path

# =================================================================
# SUPABASE CONNECTION
# =================================================================
SUPABASE_DB_URL = (
    "postgresql://postgres:SHARAN%406382031836"
    "@db.iqgpxavpimxpcyrxizji.supabase.co:5432/postgres"
)

# =================================================================
# PATHS
# =================================================================
ROOT = Path(__file__).resolve().parent.parent
TOPICS_PATH = ROOT / "data" / "topics_mapping.json"
QUESTIONS_PATH = ROOT / "data" / "all_questions.json"


def connect():
    """Connect to Supabase Postgres."""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL, sslmode="require")
        conn.autocommit = False
        print("[OK] Connected to Supabase PostgreSQL")
        return conn
    except Exception as e:
        print(f"[ERROR] Could not connect to Supabase: {e}")
        sys.exit(1)


def load_topic_map():
    """Load topics_mapping.json."""
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def drop_all_tables(conn, topic_map):
    """Drop all aptitude tables (for --reset)."""
    cur = conn.cursor()
    print("\n[RESET] Dropping all tables...")

    # Drop in correct order (foreign keys first)
    drop_order = ["quiz_answers", "quiz_results", "aptitude_questions"]
    # Add topic tables
    for table_name in topic_map.values():
        drop_order.append(table_name)

    for table in drop_order:
        try:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  + Dropped {table}")
        except Exception as e:
            conn.rollback()
            print(f"  X Failed to drop {table}: {e}")

    conn.commit()
    cur.close()
    print("[OK] All tables dropped\n")


def create_schema(conn, topic_map):
    """Create all tables in Supabase."""
    cur = conn.cursor()

    print("\n" + "=" * 46)
    print("  CREATING SCHEMA IN SUPABASE")
    print("=" * 46 + "\n")

    # -- 1. Master questions table
    print("[1/4] Creating aptitude_questions...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aptitude_questions (
            id SERIAL PRIMARY KEY,
            question TEXT UNIQUE,
            options TEXT,
            correct_answer VARCHAR(10),
            explanation TEXT,
            category VARCHAR(200),
            source VARCHAR(200)
        )
    """)
    conn.commit()
    print("  + aptitude_questions ready")

    # -- 2. Quiz results table
    print("[2/4] Creating quiz_results...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id SERIAL PRIMARY KEY,
            correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
            submitted_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    print("  + quiz_results ready")

    # -- 3. Quiz answers table
    print("[3/4] Creating quiz_answers...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id SERIAL PRIMARY KEY,
            result_id INTEGER REFERENCES quiz_results(id) ON DELETE CASCADE,
            question_id INTEGER,
            question_text TEXT,
            user_answer VARCHAR(10),
            correct_answer VARCHAR(10),
            is_correct BOOLEAN,
            answered_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    print("  + quiz_answers ready")

    # -- 4. Individual topic tables
    print(f"[4/4] Creating {len(topic_map)} topic tables...")
    created = 0
    for topic_name, table_name in topic_map.items():
        try:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    question TEXT UNIQUE,
                    options TEXT,
                    correct_answer VARCHAR(10),
                    explanation TEXT,
                    category VARCHAR(200),
                    source VARCHAR(200)
                )
            """)
            conn.commit()
            created += 1
            print(f"  + {table_name}")
        except Exception as e:
            conn.rollback()
            print(f"  X {table_name}: {e}")

    print(f"\n[OK] Schema complete: 3 core tables + {created} topic tables")
    cur.close()


def load_questions(conn, topic_map):
    """Load all_questions.json into the master + topic tables."""
    cur = conn.cursor()

    # Check current count
    cur.execute("SELECT COUNT(*) FROM aptitude_questions")
    existing = cur.fetchone()[0]

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    total = len(questions)
    print("\n" + "=" * 46)
    print(f"  LOADING {total} QUESTIONS INTO SUPABASE")
    print(f"  (existing: {existing})")
    print("=" * 46 + "\n")

    inserted_master = 0
    inserted_topic = 0
    errors = 0

    for i, q in enumerate(questions):
        try:
            # Insert into MASTER table
            cur.execute("""
                INSERT INTO aptitude_questions
                    (question, options, correct_answer, explanation, category, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (question) DO NOTHING
            """, (
                q.get("question"),
                json.dumps(q.get("options", {})),
                q.get("answer"),
                q.get("explanation"),
                q.get("category"),
                q.get("source")
            ))
            if cur.rowcount > 0:
                inserted_master += 1

            # Insert into TOPIC table
            cat = q.get("category")
            if cat in topic_map:
                table_name = topic_map[cat]
                cur.execute(f"""
                    INSERT INTO {table_name}
                        (question, options, correct_answer, explanation, category, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (question) DO NOTHING
                """, (
                    q.get("question"),
                    json.dumps(q.get("options", {})),
                    q.get("answer"),
                    q.get("explanation"),
                    q.get("category"),
                    q.get("source")
                ))
                if cur.rowcount > 0:
                    inserted_topic += 1

            # Commit every 100 for safety
            if (i + 1) % 100 == 0:
                conn.commit()
                print(f"  ... {i + 1}/{total} processed")

        except Exception as e:
            conn.rollback()
            errors += 1
            if errors <= 5:
                print(f"  [WARN] Skipped question {i + 1}: {e}")

    conn.commit()

    # Final count
    cur.execute("SELECT COUNT(*) FROM aptitude_questions")
    final = cur.fetchone()[0]

    print("\n" + "=" * 46)
    print("  LOAD COMPLETE")
    print("=" * 46)
    print(f"  Master table: {inserted_master} new rows inserted")
    print(f"  Topic tables: {inserted_topic} new rows inserted")
    print(f"  Errors:       {errors}")
    print(f"  Total in DB:  {final}")
    print("=" * 46 + "\n")

    cur.close()


def verify(conn, topic_map):
    """Print a summary of all table counts."""
    cur = conn.cursor()

    print("=" * 46)
    print("  VERIFICATION -- TABLE COUNTS")
    print("=" * 46 + "\n")

    # Core tables
    for table in ["aptitude_questions", "quiz_results", "quiz_answers"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table:.<40} {count}")
        except Exception:
            conn.rollback()
            print(f"  {table:.<40} [MISSING]")

    print()

    # Topic tables
    total_topic_rows = 0
    for topic_name, table_name in sorted(topic_map.items()):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            total_topic_rows += count
            print(f"  {table_name:.<40} {count}")
        except Exception:
            conn.rollback()
            print(f"  {table_name:.<40} [MISSING]")

    print(f"\n  {'TOTAL across topic tables':.<40} {total_topic_rows}")
    print()
    cur.close()


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    reset = "--reset" in sys.argv

    print("\n" + "=" * 46)
    print("  AptitudeIQ -- Supabase Schema Setup")
    print("=" * 46)
    print(f"  Host: db.iqgpxavpimxpcyrxizji.supabase.co")
    print(f"  Mode: {'RESET + CREATE' if reset else 'CREATE (safe)'}")
    print("=" * 46 + "\n")

    conn = connect()
    topic_map = load_topic_map()

    if reset:
        drop_all_tables(conn, topic_map)

    create_schema(conn, topic_map)
    load_questions(conn, topic_map)
    verify(conn, topic_map)

    conn.close()
    print("[DONE] Supabase setup complete!\n")
