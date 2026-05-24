"""
create_supabase_schema.py
─────────────────────────
Creates the necessary database tables in your Supabase database.

Note: The Supabase REST API (using SUPABASE_URL and SUPABASE_SERVICE_KEY) 
cannot execute DDL statements like 'CREATE TABLE'. 
To create tables programmatically, this script requires the direct 
PostgreSQL connection string.

You can find this in your Supabase Dashboard:
Project Settings -> Database -> Connection String (URI)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# We need the DIRECT PostgreSQL connection string, not the REST API URL.
# It usually looks like: postgresql://postgres.iqgpxavpimxpcyrxizji:[YOUR-PASSWORD]@aws-0-...pooler.supabase.com:6543/postgres
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    print("❌ Error: SUPABASE_DB_URL is not set in your .env file.")
    print("Please add it. It should look like:")
    print("SUPABASE_DB_URL=postgresql://postgres.iqgpxavpimxpcyrxizji:<your_db_password>@aws-0-<region>.pooler.supabase.com:6543/postgres")
    sys.exit(1)

def run():
    print("Connecting directly to Supabase PostgreSQL...")
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        print("✓ Connected successfully!")
        
        # Read the generated schema file
        with open("supabase_schema.sql", "r") as f:
            sql_script = f.read()
            
        print("Executing schema SQL script...")
        # Execute the entire script
        cursor.execute(sql_script)
        
        print("✅ Schema created successfully in Supabase!")
        print("You can now run: python migrate_to_supabase.py")
        
    except Exception as e:
        print(f"❌ Failed to create schema: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run()
