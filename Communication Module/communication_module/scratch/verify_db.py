import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def verify():
    print("=== Database Content Verification ===\n")
    
    tables = ["listening_clips", "speaking_questions"]
    
    for table in tables:
        try:
            res = supabase.table(table).select("*", count="exact").limit(2).execute()
            print(f"Table: {table}")
            print(f"  Count: {res.count} rows")
            if res.data:
                print(f"  Sample Data (First 2 rows):")
                for i, row in enumerate(res.data, 1):
                    # For listening: show clip_id. For speaking: show question_text.
                    label = row.get("clip_id") or row.get("question_text", "N/A")
                    print(f"    {i}. {label[:100]}...")
            else:
                print("  [!] Table is EMPTY")
            print("-" * 40)
        except Exception as e:
            print(f"  [X] Error checking {table}: {e}")

if __name__ == "__main__":
    verify()
