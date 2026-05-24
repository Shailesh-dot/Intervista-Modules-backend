from db import supabase_request
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
import random

STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
CORS(app)

MAP_PATH = Path(__file__).parent / "data" / "topics_mapping.json"
try:
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        TOPIC_MAP = json.load(f)
except Exception as e:
    print(f"[WARN] Could not load topics_mapping.json: {e}")
    TOPIC_MAP = {}

def ensure_tables():
    pass

def load_json_to_db(reset=False):
    import subprocess
    import sys
    print("\n[SYNC] Checking for new question files and converting to JSON...")
    convert_path = Path(__file__).parent / "scripts" / "convert.py"
    try:
        subprocess.run([sys.executable, str(convert_path)], check=True)
    except Exception as e:
        print(f"[WARN] Failed to run convert.py (is Tesseract/pdfplumber missing?): {e}")

    print("\n[SYNC] Syncing local JSON to Supabase Cloud...")
    migrate_path = Path(__file__).parent / "migrate.py"
    try:
        subprocess.run([sys.executable, str(migrate_path)])
    except Exception as e:
        print(f"[ERROR] Failed to run migrate.py: {e}")

@app.route("/api/topics")
def get_topics():
    topic_details = []
    for topic_name, table_name in TOPIC_MAP.items():
        try:
            count = supabase_request("GET", table_name, prefer="count=exact,head=true") or 0
        except Exception:
            count = 0
            
        display = topic_name.replace("_", " ")
        for prefix in ["Topic ", "Q"]:
            if display.startswith(prefix):
                display = display[len(prefix):]
        parts = display.split(" ", 1)
        if parts[0].isdigit() and len(parts) > 1:
            display = parts[1]
            
        topic_details.append({
            "key": topic_name,
            "table": table_name,
            "display": display.strip(),
            "count": count
        })

    topic_details.sort(key=lambda t: t["display"].lower())
    return jsonify({
        "topics": topic_details,
        "count": len(topic_details)
    })

@app.route("/api/questions/by-topics", methods=["POST"])
def get_questions_by_topics():
    payload = request.get_json(silent=True) or {}
    selected_topics = payload.get("topics", [])
    num_questions = payload.get("num_questions", 15)

    all_questions = []
    try:
        if not selected_topics:
            data = supabase_request("GET", "aptitude_questions", params={"select": "id,question,options,category,source", "limit": "500"})
            if data:
                all_questions.extend(data)
        else:
            for topic_key in selected_topics:
                if topic_key in TOPIC_MAP:
                    tbl = TOPIC_MAP[topic_key]
                    data = supabase_request("GET", tbl, params={"select": "id,question,options,category,source", "limit": "200"})
                    if data:
                        all_questions.extend(data)

        if not all_questions:
            return jsonify([])

        if len(all_questions) > num_questions:
            all_questions = random.sample(all_questions, num_questions)

    except Exception as e:
        print("[ERROR] get_questions_by_topics:", e)
        return jsonify({"error": str(e)}), 500

    out = []
    for r in all_questions:
        q = (r.get("question") or "").replace("**", "").replace("*", "").strip()
        opts = r.get("options")
        if isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except:
                opts = {}
        out.append({
            "id": r.get("id"),
            "question": q,
            "options": opts,
            "category": r.get("category") or "General",
            "source": r.get("source") or "",
        })
    return jsonify(out)

@app.route("/api/questions")
def get_questions():
    try:
        data = supabase_request("GET", "aptitude_questions", params={"select": "id,question,options,category,source", "limit": "300"})
        if not data:
            return jsonify([])
        
        sample = random.sample(data, min(15, len(data)))
        out = []
        for r in sample:
            q = (r.get("question") or "").replace("**", "").replace("*", "").strip()
            opts = r.get("options")
            if isinstance(opts, str):
                try:
                    opts = json.loads(opts)
                except:
                    opts = {}
            out.append({
                "id": r.get("id"),
                "question": q,
                "options": opts,
                "category": r.get("category") or "General",
                "source": r.get("source") or "",
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/save", methods=["POST"])
def save():
    payload = request.get_json(silent=True)
    if not payload or "answers" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    answers = payload["answers"]
    correct = wrong = skipped = 0
    answer_rows = []

    try:
        for item in answers:
            qid = item.get("question_id")
            user_ans = item.get("answer")

            if qid is None:
                skipped += 1
                answer_rows.append({"question_id": None, "user_answer": user_ans, "correct_answer": None, "is_correct": None, "question_text": None})
                continue

            row = supabase_request("GET", "aptitude_questions", params={"id": f"eq.{qid}", "select": "correct_answer,question"})
            if not row:
                skipped += 1
                continue
                
            correct_ans = row[0].get("correct_answer")
            question_txt = row[0].get("question")

            if user_ans is None:
                skipped += 1
                is_correct = None
            elif str(user_ans).strip().upper() == str(correct_ans).strip().upper():
                correct += 1
                is_correct = True
            else:
                wrong += 1
                is_correct = False

            answer_rows.append({
                "question_id": qid,
                "question_text": question_txt,
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct
            })

        total = len(answers)
        percentage = round(correct / total * 100, 2) if total else 0.0

        # Insert into Supabase quiz_results
        res = supabase_request(
            "POST", 
            "quiz_results", 
            json_data={
                "correct": correct, "wrong": wrong, "skipped": skipped, 
                "score": correct, "percentage": percentage
            },
            prefer="return=representation"
        )
        if not res:
            raise Exception("Failed to insert result to Supabase")
        result_id = res[0]["id"]

        for ar in answer_rows:
            ar["result_id"] = result_id
            
        if answer_rows:
            supabase_request("POST", "quiz_answers", json_data=answer_rows)

        print(f"[OK] result_id={result_id} | correct={correct} wrong={wrong} percentage={percentage}% Saved to Supabase Cloud.")
        return jsonify({"status": "saved", "result_id": result_id})

    except Exception as e:
        print("[ERROR] Save error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/debug")
def debug():
    try:
        q = supabase_request("GET", "aptitude_questions", prefer="count=exact,head=true") or 0
        r = supabase_request("GET", "quiz_results", prefer="count=exact,head=true") or 0
        a = supabase_request("GET", "quiz_answers", prefer="count=exact,head=true") or 0
        return jsonify({"aptitude_questions": q, "quiz_results": r, "quiz_answers": a})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/results")
def results():
    try:
        rows = supabase_request("GET", "quiz_results", params={"order": "submitted_at.desc", "limit": "50"}) or []
        out = []
        for r in rows:
            out.append({
                "id": r.get("id"),
                "correct": r.get("correct"),
                "wrong": r.get("wrong"),
                "skipped": r.get("skipped"),
                "score": r.get("score"),
                "percentage": float(r.get("percentage", 0)),
                "submitted_at": r.get("submitted_at")
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/results/<int:result_id>/answers")
def result_answers(result_id):
    try:
        rows = supabase_request("GET", "quiz_answers", params={"result_id": f"eq.{result_id}", "order": "id.asc"}) or []
        out = []
        for r in rows:
            out.append({
                "question_id": r.get("question_id"),
                "question": (r.get("question_text") or "")[:120],
                "user_answer": r.get("user_answer"),
                "correct_answer": r.get("correct_answer"),
                "is_correct": r.get("is_correct")
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path.startswith("api/"):
        return jsonify({"error": "API route not found"}), 404
        
    target = STATIC_DIR / path
    if path and target.exists():
        return send_from_directory(str(STATIC_DIR), path)
    return send_from_directory(str(STATIC_DIR), "index.html")

if __name__ == "__main__":
    print("\n[START] AptitudeIQ (Supabase Cloud Only) -> http://localhost:5000\n")
    load_json_to_db(reset=False)
    app.run(debug=True, use_reloader=False, port=5000)