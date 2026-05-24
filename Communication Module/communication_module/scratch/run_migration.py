import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def run_migration():
    print("=== Database Migration ===")
    
    # We will invoke an RPC call if they have one, or use postgres connection if available.
    # Since we don't have the password, we might not be able to execute DDL via REST reliably unless there's an RPC.
    # However, since Supabase python client doesn't support raw DDL via SQL (except if we use postgres directly),
    # let's try calling a function or we'll just inform the user.
    # Actually, Supabase is schemaless JSONB for anything outside predefined columns, depending on how they created it.
    print("[NOTE] Supabase REST API does not allow direct DDL execution like 'ALTER TABLE'.")
    print("If you enforced strict schema on `listening_clip_results`, please run:")
    print("  ALTER TABLE listening_clip_results RENAME COLUMN sentence_reconstruction TO comprehension;")
    print("in your Supabase SQL Editor.")

if __name__ == "__main__":
    run_migration()
