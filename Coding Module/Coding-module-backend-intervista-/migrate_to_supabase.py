"""
migrate_to_supabase.py
──────────────────────
Migrates the entire local PostgreSQL Coding Assessment DB to Supabase.

Tables migrated (in FK-safe order):
  1. users
  2. questions
  3. assessment_sessions
  4. test_cases
  5. submissions
  6. submission_results

Usage:
    python migrate_to_supabase.py

Requirements:
    pip install psycopg2-binary supabase python-dotenv
"""

import os
import json
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from supabase import create_client, Client

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

# ▶ Local PostgreSQL – pulled from your existing .env
LOCAL_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://coding_platform:secure_password@localhost:5432/coding_db"
)

# ▶ Supabase – override via env vars or set directly here
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iqgpxavpimxpcyrxizji.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlxZ3B4YXZwaW14cGN5cnhpemppIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjIyMDc0NiwiZXhwIjoyMDkxNzk2NzQ2fQ.mjy5wH26086LzLXxByI-0VSNpsjtDzC_L8uB9TLoJFo"
)

BATCH_SIZE = 100  # rows per upsert batch


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def serialize_row(row: dict) -> dict:
    """Convert any non-JSON-serialisable types (datetime, etc.) to strings."""
    clean = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, (dict, list)):
            # Ensure nested structures are also clean, though psycopg2 usually hands us dicts
            clean[k] = v
        else:
            clean[k] = v
    return clean


def fetch_all(cursor, table: str) -> list[dict]:
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    return [serialize_row(dict(r)) for r in rows]


def upsert_batched(supabase: Client, table: str, rows: list[dict]):
    """Upsert rows to Supabase in batches."""
    total = len(rows)
    if total == 0:
        log(f"  → {table}: no rows to migrate, skipping.")
        return

    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        try:
            supabase.table(table).upsert(batch, on_conflict=None).execute()
            log(f"  → {table}: upserted rows {start + 1}–{min(start + BATCH_SIZE, total)} / {total}")
        except Exception as e:
            log(f"  ✗ ERROR upserting {table} batch starting at {start}: {e}")
            raise


def run_migration():
    log("=== Coding Assessment DB → Supabase Migration ===")

    # ── Connect to local Postgres ──────────────────────────────────────────────
    log("Connecting to local PostgreSQL …")
    try:
        conn = psycopg2.connect(LOCAL_DB_URL)
        conn.set_client_encoding("UTF8")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log("✓ Connected to local DB")
    except Exception as e:
        log(f"✗ Could not connect to local DB: {e}")
        sys.exit(1)

    # ── Connect to Supabase ────────────────────────────────────────────────────
    log("Connecting to Supabase (API) …")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        log("✓ Connected to Supabase API")
    except Exception as e:
        log(f"✗ Could not connect to Supabase: {e}")
        conn.close()
        sys.exit(1)

    # ── Create Supabase Tables if they do not exist ────────────────────────────
    # For this to work without psql/pg_dump, we connect directly using SQLAlchemy 
    # to the Supabase connection string. We can construct it from the user's Supabase dashboard
    # However, since we don't have the direct Postgres connection string to Supabase, 
    # we can instruct the user to run the schema dump we made in Supabase's SQL Editor.
    # Actually wait - Supabase provides Postgres running on port 5432!
    
    log("Checking Supabase Schema...")
    log("""
    ⚠️  IMPORTANT: Supabase requires tables to exist before upserting data!
    Because your script returned PGRST205 (table not found in schema cache), 
    you must first create the tables in Supabase.
    
    I have generated 'supabase_schema.sql' in this folder.
    
    ACTION REQUIRED BEFORE MIGRATING:
    1. Open your Supabase Dashboard -> SQL Editor.
    2. Open 'supabase_schema.sql', copy all contents.
    3. Paste into the SQL Editor and click 'RUN'.
    4. Then re-run this script!
    """)
    
    # We will still try to migrate, but it will print the same error if they haven't done it.
    
    # ── Migration order (respects FK dependencies) ─────────────────────────────
    tables_in_order = [
        "users",
        "questions",
        "assessment_sessions",
        "test_cases",
        "submissions",
        "submission_results",
    ]

    summary = {}

    for table in tables_in_order:
        log(f"\nMigrating table: {table} …")
        try:
            rows = fetch_all(cursor, table)
            summary[table] = len(rows)
            log(f"  Fetched {len(rows)} rows from local DB")
            upsert_batched(supabase, table, rows)
            log(f"  ✓ {table} done")
        except psycopg2.errors.UndefinedTable:
            log(f"  ⚠ Table '{table}' does not exist locally – skipping.")
            summary[table] = 0
        except Exception as e:
            log(f"  ✗ Failed on {table}: {e}")
            summary[table] = -1

    # ── Summary ────────────────────────────────────────────────────────────────
    cursor.close()
    conn.close()

    log("\n\n=== MIGRATION SUMMARY ===")
    for table, count in summary.items():
        if count == -1:
            status = "FAILED"
        elif count == 0:
            status = "SKIPPED (empty / missing)"
        else:
            status = f"{count} rows migrated"
        log(f"  {table:<25} {status}")
    log("=========================")
    log("Migration complete.")


if __name__ == "__main__":
    run_migration()
