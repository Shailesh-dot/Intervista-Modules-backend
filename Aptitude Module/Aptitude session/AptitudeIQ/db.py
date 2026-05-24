import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

def supabase_request(method, table, params=None, json_data=None, prefer=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] Supabase credentials not found in environment variables.")
        return None

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    if prefer:
        headers["Prefer"] = prefer
        
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    
    try:
        r = requests.request(method, url, headers=headers, params=params, json=json_data)
        if r.status_code >= 400:
            print(f"[ERROR] Supabase Error: {r.status_code} - {r.text}")
            return None
        
        # Handle exact count for GET/HEAD
        if prefer and "count=exact" in prefer:
            cr = r.headers.get("Content-Range")
            if cr and "/" in cr:
                try:
                    return int(cr.split("/")[-1])
                except: pass
            return 0
            
        if r.text:
            return r.json()
    except Exception as e:
        print(f"[ERROR] Supabase connection failure ({method} {table}): {e}")
        return None
    
    return None

def get_connection():
    # Deprecated: PGAdmin local connection is no longer supported.
    print("[WARN] get_connection() is deprecated. Use supabase_request() instead.")
    return None