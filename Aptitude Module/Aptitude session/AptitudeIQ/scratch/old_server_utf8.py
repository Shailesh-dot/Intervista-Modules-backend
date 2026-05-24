from db import get_connection
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json

# React build output goes to  AptitudeIQ/static/
STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
CORS(app)


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# TOPIC MAPPING ΓÇö Load from JSON
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
MAP_PATH = Path(__file__).parent / "data" / "topics_mapping.json"
try:
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        TOPIC_MAP = json.load(f)
except Exception as e:
    print(f"[WARN] Could not load topics_mapping.json: {e}")
    TOPIC_MAP = {}

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# TABLE SETUP ΓÇö run once on startup
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
def ensure_tables():
    conn = get_connection()
    if conn is None:
        print("[ERROR] DB not connected ΓÇö cannot create tables")
        return
    cur = conn.cursor()
    try:
        # 1. Create Base Tables
        tables = {
            "aptitude_questions": """
                CREATE TABLE IF NOT EXISTS aptitude_questions (
                    id SERIAL PRIMARY KEY,
                    question TEXT UNIQUE,
                    options TEXT,
                    correct_answer VARCHAR(10),
                    explanation TEXT,
                    category VARCHAR(200),
                    source VARCHAR(200)
                )
            """,
            "quiz_results": """
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id SERIAL PRIMARY KEY,
                    correct INTEGER NOT NULL DEFAULT 0,
                    wrong INTEGER NOT NULL DEFAULT 0,
                    skipped INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
                    submitted_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """,
            "quiz_answers": """
                CREATE TABLE IF NOT EXISTS quiz_answers (
                    id SERIAL PRIMARY KEY,
                    result_id INTEGER REFERENCES quiz_results(id) ON DELETE CASCADE,
                    question_id INTEGER,
                    question_text TEXT,
                    user_answer VARCHAR(10),
                    correct_answer VARCHAR(10),
                    is_correct BOOLEAN,
                    answered_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """
        }
        for name, sql in tables.items():
            try:
                cur.execute(sql)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"[WARN] Failed to create {name}: {e}")

        # 2. Create Topic Tables
        for topic_name, table_name in TOPIC_MAP.items():
            try:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        question TEXT UNIQUE,
                        options TEXT,
                        correct_answer VARCHAR(10),
                        explanation TEXT,
                        category VARCHAR(200),
                        source VARCHAR(200)
                    )
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"[WARN] Failed to create {table_name}: {e}")

        # 3. Add Constraints
        try:
            cur.execute("ALTER TABLE aptitude_questions ADD CONSTRAINT unique_question UNIQUE (question)")
            conn.commit()
        except Exception:
            conn.rollback() 
        print(f"[OK] Master table + {len(TOPIC_MAP)} topic tables ready")
    except Exception as e:
        # Ignore if constraint already exists
        conn.rollback()
        print(f"[WARN] Table setup warning: {e}")

    finally:
        cur.close()
        conn.close()


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# LOAD JSON ΓåÆ POSTGRES  (skips if already populated)
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
def load_json_to_db(reset=False):
    conn = get_connection()
    if conn is None:
        print("[ERROR] DB not connected")
        return
    cur = conn.cursor()
    try:
        if reset:
            print("[WARN] Clearing all tablesΓÇª")
            cur.execute("TRUNCATE TABLE aptitude_questions RESTART IDENTITY CASCADE")
            for table_name in TOPIC_MAP.values():
                try:
                    cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                except:
                    pass
            conn.commit()
            initial_count = 0
        else:
            cur.execute("SELECT COUNT(*) FROM aptitude_questions")
            initial_count = cur.fetchone()[0]

        json_path = Path(__file__).parent / "data" / "all_questions.json"
        with open(json_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        print(f"[LOAD] Loading {len(questions)} questionsΓÇª")
        inserted = 0

        for q in questions:
            try:
                # 1. Insert into MASTER table
                cur.execute("""
                    INSERT INTO aptitude_questions
                        (question, options, correct_answer, explanation, category, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (question) DO NOTHING
                """, (
                    q.get("question"),
                    json.dumps(q.get("options", {})),
                    q.get("answer"),
                    q.get("explanation"),
                    q.get("category"),
                    q.get("source")
                ))
                is_new = cur.rowcount > 0

                # 2. Insert into TOPIC table
                cat = q.get("category")
                if cat in TOPIC_MAP:
                    table_name = TOPIC_MAP[cat]
                    cur.execute(f"""
                        INSERT INTO {table_name}
                            (question, options, correct_answer, explanation, category, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (question) DO NOTHING
                    """, (
                        q.get("question"),
                        json.dumps(q.get("options", {})),
                        q.get("answer"),
                        q.get("explanation"),
                        q.get("category"),
                        q.get("source")
                    ))

                if is_new:
                    inserted += 1
                
                # Commit every 100 questions for speed/safety
                if inserted % 100 == 0:
                    conn.commit()

            except Exception as e:
                # Rollback ONLY this question's failed insertion
                conn.rollback()
                print(f"[WARN] Skipped question: {e}")

        conn.commit()
        cur.execute("SELECT COUNT(*) FROM aptitude_questions")
        final_count = cur.fetchone()[0]
        
        print(f"[OK] {initial_count} existing questions | {inserted} new questions added | Total: {final_count}")
    except Exception as e:
        conn.rollback()
        print("[ERROR] Load error:", e)
    finally:
        cur.close()
        conn.close()


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# SERVE REACT FRONTEND
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # API routes are handled before this catch-all
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    target = STATIC_DIR / path
    if path and target.exists():
        return send_from_directory(str(STATIC_DIR), path)
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/topics")
def get_topics():
    return jsonify({
        "mapping": TOPIC_MAP,
        "count": len(TOPIC_MAP)
    })


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# API ΓÇö GET 15 RANDOM QUESTIONS
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
@app.route("/api/questions")
def get_questions():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB not connected"}), 500

    cur = conn.cursor()
    cur.execute("""
        SELECT id, question, options, category, source
        FROM   aptitude_questions
        ORDER  BY RANDOM()
        LIMIT  15
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = []
    for r in rows:
        q = (r[1] or "").strip()
        # Only strip residual markdown noise ΓÇö converter handles most cleanup
        q = q.replace("**", "").replace("*", "").strip()

        opts = r[2]
        if isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except Exception:
                opts = {}

        data.append({
            "id"      : r[0],
            "question": q.strip(),
            "options" : opts,
            "category": r[3] or "General",
            "source"  : r[4] or "",
        })

    return jsonify(data)


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# API ΓÇö SAVE ANSWERS & EVALUATE ENTIRELY IN POSTGRES
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
@app.route("/api/save", methods=["POST"])
def save():
    payload = request.get_json(silent=True)
    if not payload or "answers" not in payload:
        return jsonify({"error": "Invalid payload ΓÇö expected {answers:[...]}"}), 400

    answers = payload["answers"]   # [{question_id, answer}, ...]

    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB not connected"}), 500

    cur = conn.cursor()
    correct = wrong = skipped = 0
    answer_rows = []

    try:
        for item in answers:
            qid      = item.get("question_id")
            user_ans = item.get("answer")          # None  ΓåÆ skipped

            if qid is None:
                skipped += 1
                answer_rows.append((None, user_ans, None, None))
                continue

            # ΓöÇΓöÇ Look up correct answer in Postgres ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
            cur.execute(
                "SELECT correct_answer, question FROM aptitude_questions WHERE id = %s",
                (qid,)
            )
            row = cur.fetchone()

            if not row:
                print(f"[WARN] Question id {qid} not found in DB")
                skipped += 1
                answer_rows.append((qid, None, user_ans, None, None))
                continue

            correct_ans = row[0]
            question_txt = row[1]

            if user_ans is None:
                skipped += 1
                is_correct = None
            elif str(user_ans).strip().upper() == str(correct_ans).strip().upper():
                correct += 1
                is_correct = True
            else:
                wrong += 1
                is_correct = False

            answer_rows.append((qid, question_txt, user_ans, correct_ans, is_correct))

        total      = len(answers)
        percentage = round(correct / total * 100, 2) if total else 0.0

        # ΓöÇΓöÇ Insert summary row ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        cur.execute("""
            INSERT INTO quiz_results (correct, wrong, skipped, score, percentage)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (correct, wrong, skipped, correct, percentage))

        result_id = cur.fetchone()[0]

        # ΓöÇΓöÇ Insert per-answer detail rows ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        for (qid, question_txt, user_ans, correct_ans, is_correct) in answer_rows:
            cur.execute("""
                INSERT INTO quiz_answers
                    (result_id, question_id, question_text, user_answer, correct_answer, is_correct)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (result_id, qid, question_txt, user_ans, correct_ans, is_correct))

        conn.commit()
        print(f"[OK] result_id={result_id} | correct={correct} wrong={wrong} "
              f"skipped={skipped} pct={percentage}%")
        return jsonify({"status": "saved", "result_id": result_id})

    except Exception as e:
        conn.rollback()
        print("[ERROR] Save error:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# DEBUG / VERIFY ENDPOINTS
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
@app.route("/api/debug")
def debug():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB not connected"}), 500
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM aptitude_questions")
    q = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quiz_results")
    r = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quiz_answers")
    a = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({"aptitude_questions": q, "quiz_results": r, "quiz_answers": a})


@app.route("/api/results")
def results():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB not connected"}), 500
    cur = conn.cursor()
    cur.execute("""
        SELECT id, correct, wrong, skipped, score, percentage, submitted_at
        FROM   quiz_results
        ORDER  BY submitted_at DESC
        LIMIT  50
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        "id": r[0], "correct": r[1], "wrong": r[2], "skipped": r[3],
        "score": r[4], "percentage": float(r[5]), "submitted_at": str(r[6])
    } for r in rows])


@app.route("/api/results/<int:result_id>/answers")
def result_answers(result_id):
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB not connected"}), 500
    cur = conn.cursor()
    cur.execute("""
        SELECT qa.question_id, aq.question, qa.user_answer,
               qa.correct_answer, qa.is_correct
        FROM   quiz_answers qa
        LEFT JOIN aptitude_questions aq ON aq.id = qa.question_id
        WHERE  qa.result_id = %s
        ORDER  BY qa.id
    """, (result_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        "question_id": r[0], "question": (r[1] or "")[:120],
        "user_answer": r[2], "correct_answer": r[3], "is_correct": r[4]
    } for r in rows])


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# ENTRY POINT
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
if __name__ == "__main__":
    print("\n[START] AptitudeIQ  ΓåÆ  http://localhost:5000\n")
    ensure_tables()
    load_json_to_db(reset=False)
    app.run(debug=True, use_reloader=False, port=5000)
