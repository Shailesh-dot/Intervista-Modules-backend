import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Parse DATABASE_URL
DB_URL = os.getenv("DATABASE_URL")

try:
    print(f"Connecting to Postgres to execute schema update...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'listening_clip_results';")
    columns = [col[0] for col in cursor.fetchall()]
    
    print("Existing columns:", columns)
    
    if "sentence_reconstruction" in columns:
        print("Found 'sentence_reconstruction' column. Renaming to 'comprehension'...")
        cursor.execute("ALTER TABLE listening_clip_results RENAME COLUMN sentence_reconstruction TO comprehension;")
        print("Column renamed successfully.")
    elif "comprehension" in columns:
        print("'comprehension' column already exists. No action needed.")
    else:
        print("WARNING: Neither 'sentence_reconstruction' nor 'comprehension' found! You might need to add it manually.")
        print("Executing fallback: ALTER TABLE listening_clip_results ADD COLUMN comprehension jsonb;")
        cursor.execute("ALTER TABLE listening_clip_results ADD COLUMN comprehension jsonb;")
        print("Column added successfully.")
        
    cursor.close()
    conn.close()
    print("Database schema update complete.")
except Exception as e:
    print(f"ERROR: {e}")
