import psycopg2

conn = psycopg2.connect(
    host='3.111.225.200',
    port=5432,
    dbname='postgres',
    user='postgres.ukdiydoqhirukeqwlpld',
    password='RUDHRITHSANDY040505',
    sslmode='require',
    connect_timeout=30
)
conn.autocommit = True
cur = conn.cursor()

# Step 1: Check actual column types
print("=== identity_verifications columns ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'identity_verifications'
    ORDER BY ordinal_position;
""")
rows = cur.fetchall()
for r in rows:
    print(r)

# Step 2: Check if columns are 'text' and need fixing
text_cols = [r[0] for r in rows if r[0] in ('id', 'user_id') and r[1] == 'text']
print(f"\nColumns that need fixing (text -> integer): {text_cols}")

if not text_cols:
    print("No columns need fixing. Types are already correct.")
    cur.close()
    conn.close()
    exit(0)

# Step 3: Drop FK constraint if it exists
print("\nDropping FK constraint if exists...")
cur.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'FK_identity_verifications_users_user_id'
            AND table_name = 'identity_verifications'
        ) THEN
            ALTER TABLE identity_verifications
                DROP CONSTRAINT "FK_identity_verifications_users_user_id";
            RAISE NOTICE 'FK dropped.';
        ELSE
            RAISE NOTICE 'FK did not exist.';
        END IF;
    END $$;
""")
print("Done.")

# Step 4: Fix 'id' if it's text
if 'id' in text_cols:
    print("\nConverting 'id' from text to integer...")
    cur.execute("ALTER TABLE identity_verifications ALTER COLUMN id TYPE integer USING id::integer;")
    print("Done.")

# Step 5: Fix 'user_id' if it's text
if 'user_id' in text_cols:
    print("\nConverting 'user_id' from text to integer...")
    cur.execute("ALTER TABLE identity_verifications ALTER COLUMN user_id TYPE integer USING user_id::integer;")
    print("Done.")

# Step 6: Re-add FK constraint
print("\nRe-adding FK constraint...")
cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'FK_identity_verifications_users_user_id'
            AND table_name = 'identity_verifications'
        ) THEN
            ALTER TABLE identity_verifications
                ADD CONSTRAINT "FK_identity_verifications_users_user_id"
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
            RAISE NOTICE 'FK re-added.';
        ELSE
            RAISE NOTICE 'FK already exists.';
        END IF;
    END $$;
""")
print("Done.")

# Step 7: Verify final state
print("\n=== Final column types ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'identity_verifications'
    ORDER BY ordinal_position;
""")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
print("\nFix complete!")
