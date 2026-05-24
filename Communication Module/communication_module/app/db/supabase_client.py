"""
supabase_client.py
───────────────────
Singleton Supabase client — used by all modules for DB access.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
