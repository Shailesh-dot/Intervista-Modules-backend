import json
import urllib.request
import urllib.error
import time
from pathlib import Path

# =================================================================
# SUPABASE CONFIGURATION
# =================================================================
SUPABASE_URL = "https://iqgpxavpimxpcyrxizji.supabase.co"
SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlx"
    "Z3B4YXZwaW14cGN5cnhpemppIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjIyM"
    "Dc0NiwiZXhwIjoyMDkxNzk2NzQ2fQ.mjy5wH26086LzLXxByI-0VSNpsjtDzC_L8uB9TLoJFo"
)

# =================================================================
# PATHS
# =================================================================
ROOT = Path(__file__).resolve().parent
TOPICS_PATH = ROOT / "data" / "topics_mapping.json"
QUESTIONS_PATH = ROOT / "data" / "all_questions.json"

import sys
sys.stdout.reconfigure(encoding='utf-8')

def insert_batch_rest(table_name, rows_batch):
    """Inserts a batch of rows to a Supabase table via REST API."""
    if not rows_batch:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    # Add on_conflict query param to make resolution=merge-duplicates work (upsert on question column)
    url += "?on_conflict=question"

    data = json.dumps(rows_batch).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        urllib.request.urlopen(req)
        return len(rows_batch)
    except urllib.error.HTTPError as e:
        error_info = e.read().decode('utf-8')
        print(f"\n[ERROR] HTTP {e.code} on table '{table_name}': {e.reason}")
        print(f"Details: {error_info}")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Failed to insert to '{table_name}': {e}")
        return 0

def run_migration():
    print("==============================================")
    print("  Supabase Data Migration (REST API)")
    print("==============================================\n")

    # Load topic maps
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        topic_map = json.load(f)

    # Load data
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    total_qs = len(questions)
    print(f"[*] Loaded {total_qs} questions from data/all_questions.json")
    print("[*] Starting migration in batches of 100...\n")

    BATCH_SIZE = 100
    total_master_inserts = 0
    topic_inserts_counts = {t: 0 for t in topic_map.values()}

    for i in range(0, total_qs, BATCH_SIZE):
        batch = questions[i:i+BATCH_SIZE]
        
        # Prepare rows for `aptitude_questions` (master)
        master_rows = []
        topic_batches = {}

        for q in batch:
            row = {
                "question": q.get("question"),
                "options": json.dumps(q.get("options", {})),
                "correct_answer": q.get("answer"),
                "explanation": q.get("explanation"),
                "category": q.get("category"),
                "source": q.get("source")
            }
            master_rows.append(row)

            # Route to correct topic table based on category
            cat = q.get("category")
            if cat in topic_map:
                table_name = topic_map[cat]
                if table_name not in topic_batches:
                    topic_batches[table_name] = []
                topic_batches[table_name].append(row)

        # 1. Insert to master table
        inserted = insert_batch_rest("aptitude_questions", master_rows)
        total_master_inserts += inserted

        # 2. Insert to respective topic tables
        for table_name, rows in topic_batches.items():
            inserted = insert_batch_rest(table_name, rows)
            topic_inserts_counts[table_name] += inserted

        # Simple terminal progress indicator
        print(f"  ... Processed {min(i + BATCH_SIZE, total_qs)} / {total_qs} questions")
        time.sleep(0.5)  # slight pause to avoid hammering the free tier API rate limits

    print("\n==============================================")
    print("  MIGRATION COMPLETE")
    print("==============================================")
    print(f"  Master 'aptitude_questions': {total_master_inserts} inserted")
    topic_total = sum(topic_inserts_counts.values())
    print(f"  Topic tables (combined):     {topic_total} inserted")
    print("==============================================\n")

if __name__ == "__main__":
    run_migration()
