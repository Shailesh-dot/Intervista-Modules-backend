"""
llama_service.py  v2
─────────────────────
ONE LLM call evaluates grammar + comprehension for all speaking questions together.

Old system: 2 LLM calls × 3 questions = 6 calls per session
New system: 1 LLM call  × 1 session   = 1 call  per session  (83% reduction)

The prompt passes all Q+A pairs together and returns structured JSON
with per-question scores that the pipeline unpacks.
"""

import json
import re
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────────────────────────────────────
# Combined grammar + comprehension prompt (all questions in one call)
# ─────────────────────────────────────────────────────────────────────────────

COMBINED_SPEAKING_PROMPT = """You are an expert English communication assessor evaluating a candidate's spoken interview responses. Your task is to assess GRAMMAR and COMPREHENSION for each answer in a single evaluation pass.

You will receive 1–3 question-answer pairs. Evaluate every pair independently.

---

## GRAMMAR RUBRIC

### Do NOT penalise (natural spoken English / Indian English):
- Sentence-initial fillers: "So", "Well", "You know", "Like", "Basically"
- Contracted forms: "gonna", "wanna", "kinda" in informal contexts
- Indian-English constructions: "I am having 5 years experience", "itself", "only" as emphasis
- Minor repetitions / false starts: "I — I worked on..." (transcription artifact)
- Omission of articles in lists: "I worked on frontend, backend, and database"

### Actively detect:
- **[TENSE]** Tense inconsistency or wrong tense
- **[SVA]** Subject-verb agreement breakdown
- **[ARTICLE]** Missing, extra, or wrong article (a/an/the)
- **[PREP]** Wrong or missing preposition
- **[WF]** Wrong word form (noun/verb/adjective confusion)
- **[STRUCT]** Broken or incoherent sentence structure

### Grammar scoring (return as float, nearest 0.5):
- 2.0 → Zero or one negligible error
- 1.5 → Minor errors (2–3), meaning still clear
- 1.0 → Noticeable errors (4–5 across categories)
- 0.5 → Frequent errors
- 0.0 → Broken grammar, meaning obscured

---

## COMPREHENSION RUBRIC

Evaluate how well the candidate's answer addresses the question — MEANING and RELEVANCE only, not grammar.

### Accept as valid (do NOT penalise):
- Informal phrasing, Indian English patterns
- Short but on-topic answers
- Thinking-aloud phrases ("so basically", "like", "you know")
- Any relevant content, even if imperfectly expressed

### Two components to score (each 0–1):
- **relevance**: Does the answer address what was asked? (0 = off-topic, 1 = fully on-topic)
- **completeness**: Does it cover the main points the question requires? (0 = missing everything, 1 = thorough)

### Comprehension note: one sentence summarising what was addressed and what was missing.

---

## INPUT

{qa_pairs}

---

## OUTPUT

Return ONLY a valid JSON object — no markdown, no preamble, no explanation.

Schema:
{{
  "results": [
    {{
      "question_index": <0-based int>,
      "grammar": {{
        "score": <float: 0.0|0.5|1.0|1.5|2.0>,
        "mistakes": [
          {{"category": "<TAG>", "original": "<wrong phrase>", "corrected": "<corrected phrase>"}}
        ],
        "note": "<one sentence grammar summary>"
      }},
      "comprehension": {{
        "relevance": <float 0–1>,
        "completeness": <float 0–1>,
        "note": "<one sentence: what was addressed and what was missing>"
      }}
    }}
  ]
}}

Return exactly as many result objects as there are input question-answer pairs.
List at most 3 grammar mistakes per answer (the most impactful ones).
If there are no grammar mistakes: return "mistakes": [].
"""


def _build_qa_block(questions_and_answers: list[dict]) -> str:
    """
    questions_and_answers: list of {"question": str, "answer": str}
    Returns formatted block for prompt injection.
    """
    lines = []
    for i, qa in enumerate(questions_and_answers):
        q = qa.get("question", "").strip() or "(no question)"
        a = qa.get("answer", "").strip()  or "(no answer)"
        lines.append(f"Question {i + 1}: {q}")
        lines.append(f"Answer {i + 1}: \"\"\"{a}\"\"\"")
        lines.append("")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _default_grammar(score: float = 1.0) -> dict:
    return {"score": score, "mistakes": [], "note": "Could not evaluate grammar"}


def _default_comprehension() -> dict:
    return {"relevance": 0.5, "completeness": 0.5, "score": 1,
            "note": "Could not evaluate comprehension"}


def _parse_result(raw: dict) -> tuple[dict, dict]:
    """Parse a single result object → (grammar_dict, comprehension_dict)."""
    # Grammar
    g_raw = raw.get("grammar", {})
    try:
        g_score = float(g_raw.get("score", 1.0))
        if g_score not in (0.0, 0.5, 1.0, 1.5, 2.0):
            # Snap to nearest valid value
            g_score = round(round(g_score * 2) / 2 * 10) / 10
    except (TypeError, ValueError):
        g_score = 1.0

    raw_mistakes = g_raw.get("mistakes", [])
    mistakes = []
    for m in raw_mistakes[:3]:
        if isinstance(m, dict):
            mistakes.append({
                "category":  m.get("category", ""),
                "original":  m.get("original", ""),
                "corrected": m.get("corrected", ""),
            })
        elif isinstance(m, str):
            mistakes.append({"category": "", "original": m, "corrected": ""})

    grammar = {
        "score":    g_score,
        "mistakes": mistakes,
        "note":     g_raw.get("note", "").strip() or (
            "Grammatically strong" if g_score >= 1.5
            else "Some grammatical issues present" if g_score >= 1.0
            else "Multiple grammatical errors detected"
        ),
    }

    # Comprehension
    c_raw = raw.get("comprehension", {})
    try:
        relevance    = max(0.0, min(1.0, float(c_raw.get("relevance",    0.5))))
        completeness = max(0.0, min(1.0, float(c_raw.get("completeness", 0.5))))
    except (TypeError, ValueError):
        relevance = completeness = 0.5

    # Also compute integer score for backward compatibility (scoring_engine uses relevance+completeness)
    raw_score_01 = relevance * 0.6 + completeness * 0.4
    int_score    = 2 if raw_score_01 >= 0.75 else (1 if raw_score_01 >= 0.40 else 0)

    comprehension = {
        "relevance":    round(relevance, 3),
        "completeness": round(completeness, 3),
        "score":        int_score,          # kept for backward compat
        "note":         c_raw.get("note", "").strip() or (
            "Fully addressed the question" if int_score == 2
            else "Partially addressed the question"
            if int_score == 1
            else "Response did not address the question"
        ),
    }

    return grammar, comprehension


def evaluate_speaking_session(
    questions_and_answers: list[dict],
    max_retries: int = 2,
) -> list[dict]:
    """
    Single LLM call evaluating all Q+A pairs for grammar + comprehension.

    Args:
        questions_and_answers: list of {"question": str, "answer": str}

    Returns:
        list of {"grammar": {...}, "comprehension": {...}} — one per input pair,
        in the same order.
    """
    n = len(questions_and_answers)

    # Fast-path: nothing to evaluate
    if n == 0:
        return []

    # Fast-path: all answers empty
    if all(
        not qa.get("answer", "").strip()
        for qa in questions_and_answers
    ):
        return [
            {"grammar": _default_grammar(1.0), "comprehension": _default_comprehension()}
            for _ in range(n)
        ]

    qa_block = _build_qa_block(questions_and_answers)
    prompt   = COMBINED_SPEAKING_PROMPT.replace("{qa_pairs}", qa_block)

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
            )
            raw_text = response.choices[0].message.content
            data     = _extract_json(raw_text)

            results_raw = data.get("results", [])
            if not results_raw:
                print(f"[SPEAKING_LLM] Empty results on attempt {attempt + 1}, retrying…")
                continue

            # Parse each result
            output = []
            for item in results_raw[:n]:
                grammar, comprehension = _parse_result(item)
                output.append({"grammar": grammar, "comprehension": comprehension})

            # Pad with defaults if model returned fewer results than questions
            while len(output) < n:
                output.append({
                    "grammar":       _default_grammar(1.0),
                    "comprehension": _default_comprehension(),
                })

            # Debug logging
            for i, item in enumerate(output):
                g = item["grammar"]
                c = item["comprehension"]
                print(
                    f"[Q{i+1}] GRAMMAR score={g['score']} mistakes={len(g['mistakes'])} | "
                    f"COMPREHENSION relevance={c['relevance']} completeness={c['completeness']}"
                )
                for j, m in enumerate(g["mistakes"], 1):
                    print(
                        f"  [{j}] {m.get('category','?')} | "
                        f"❌ \"{m.get('original')}\" → ✅ \"{m.get('corrected')}\""
                    )

            return output

        except Exception as e:
            print(f"[SPEAKING_LLM] ERROR attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                return [
                    {"grammar": _default_grammar(1.0), "comprehension": _default_comprehension()}
                    for _ in range(n)
                ]

    return [
        {"grammar": _default_grammar(1.0), "comprehension": _default_comprehension()}
        for _ in range(n)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Legacy single-question wrappers  (kept for backward compatibility with tests)
# These now internally call the batch evaluator with a single-item list.
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_grammar(text: str, question: str = "") -> dict:
    """Legacy wrapper — evaluates a single transcript. Use evaluate_speaking_session for batching."""
    results = evaluate_speaking_session([{"question": question, "answer": text}])
    return results[0]["grammar"] if results else _default_grammar(1.0)


def evaluate_comprehension(question: str, answer: str) -> dict:
    """Legacy wrapper — evaluates a single Q+A. Use evaluate_speaking_session for batching."""
    results = evaluate_speaking_session([{"question": question, "answer": answer}])
    return results[0]["comprehension"] if results else _default_comprehension()