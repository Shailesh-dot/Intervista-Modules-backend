import json
import os

TOPICS_MAP_FILE = "data/topics_mapping.json"
SQL_OUTPUT_FILE = "supabase_schema.sql"

def run():
    with open(TOPICS_MAP_FILE, "r") as f:
        topics = json.load(f)

    sql_statements = []

    sql_statements.append("-- 1. Master questions table")
    sql_statements.append("""CREATE TABLE IF NOT EXISTS aptitude_questions (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);""")

    sql_statements.append("\n-- 2. Quiz results table")
    sql_statements.append("""CREATE TABLE IF NOT EXISTS quiz_results (
    id SERIAL PRIMARY KEY,
    correct INTEGER NOT NULL DEFAULT 0,
    wrong INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);""")

    sql_statements.append("\n-- 3. Quiz answers table")
    sql_statements.append("""CREATE TABLE IF NOT EXISTS quiz_answers (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES quiz_results(id) ON DELETE CASCADE,
    question_id INTEGER,
    question_text TEXT,
    user_answer VARCHAR(10),
    correct_answer VARCHAR(10),
    is_correct BOOLEAN,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);""")

    sql_statements.append("\n-- 4. Individual topic tables")
    for topic_name, table_name in topics.items():
        sql_statements.append(f"""CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);""")

    with open(SQL_OUTPUT_FILE, "w") as f:
        f.write("\n".join(sql_statements))
    
    print(f"Generated {SQL_OUTPUT_FILE}")

if __name__ == "__main__":
    run()
