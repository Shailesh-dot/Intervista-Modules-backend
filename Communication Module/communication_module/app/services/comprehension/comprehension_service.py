import json
import re
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# NOTE: Uses .replace() instead of .format() to avoid Python treating
# JSON braces in the prompt as format placeholders (which corrupts the prompt).
COMPREHENSION_PROMPT = """You are an expert communication assessment evaluator specializing in evaluating spoken English responses from Indian professionals in interview and assessment contexts.

Your job is to evaluate how well the candidate's spoken answer addresses the given question — focusing purely on MEANING, INTENT, and RELEVANCE. You are not a grammar checker.

---

QUESTION:
\"\"\"{{QUESTION}}\"\"\"

CANDIDATE'S SPOKEN ANSWER (auto-transcribed from speech):
\"\"\"{{ANSWER}}\"\"\"

---

EVALUATION FRAMEWORK:

Step 1 — Establish what a correct answer requires:
Identify the core information or intent the question is asking for.

Step 2 — Map what the candidate actually said:
Look past filler words, repetition, informal phrasing, and Indian English patterns.
Accept these as perfectly valid:
  - "I am having experience in..." instead of "I have experience in..."
  - "only" used for emphasis ("I told him only")
  - Missing articles ("I went to office")
  - Code-mixed phrasing, colloquial transitions
  - Informal sentence structure in spoken form
  - Thinking-aloud phrases: "so basically", "like", "you know", "actually"

Step 3 — Judge relevance honestly:
  - Does the candidate demonstrate they understood the question?
  - Is the core meaning of their answer aligned with what was asked?
  - Even a partial, simple, or brief answer that is ON-TOPIC counts.

Step 4 — Assign score using THESE EXACT criteria:

  SCORE 2 — Addressed the question well:
    The answer clearly responds to what was asked. The candidate understood the question
    and gave a relevant response covering the main point(s). Minor omissions are fine.
    Give 2 generously when intent is clear and content is on-topic.

  SCORE 1 — Partially addressed:
    The answer touches on the topic but is vague, incomplete, drifts off-topic partway,
    or only answers one part of a multi-part question. Still relevant but notably lacking.

  SCORE 0 — Did not address the question:
    ONLY use this when the answer is entirely off-topic, completely irrelevant,
    nonsensical, or the candidate clearly did not understand what was asked.
    Do NOT use 0 just because the answer is short, informal, or imperfectly worded.
    Do NOT use 0 if there is ANY relevant content present.

BIAS WARNING: LLMs tend to be stricter than necessary with spoken transcriptions.
Consciously correct for this. When in doubt between 0 and 1, choose 1.
When in doubt between 1 and 2, choose 2 if the intent is clearly aligned.

---

RESPOND WITH ONLY THIS JSON (no explanation, no markdown, no extra text):
{"score": <0 or 1 or 2>, "note": "<one sentence: what they addressed and what was missing if anything>"}"""


def _build_prompt(question: str, answer: str) -> str:
    """
    Uses .replace() instead of .format() to safely inject values
    without Python misinterpreting JSON braces as format placeholders.
    """
    return (
        COMPREHENSION_PROMPT
        .replace("{{QUESTION}}", question)
        .replace("{{ANSWER}}", answer)
    )


def _extract_json(text: str) -> dict:
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()

    # Direct parse attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: find first {...} block
    match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: extract score digit manually
    score_match = re.search(r'"score"\s*:\s*([012])', cleaned)
    note_match = re.search(r'"note"\s*:\s*"([^"]+)"', cleaned)
    if score_match:
        return {
            "score": int(score_match.group(1)),
            "note": note_match.group(1) if note_match else ""
        }

    return {}


def evaluate_comprehension(question: str, answer: str, max_retries: int = 2) -> dict:
    if not question or not answer or not answer.strip():
        return {"score": 1, "note": "No answer provided to evaluate"}

    prompt = _build_prompt(question.strip(), answer.strip())

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            raw = response.choices[0].message.content
           

            data = _extract_json(raw)

            if not data:
                print(f"[COMPREHENSION] JSON extraction failed on attempt {attempt + 1}, retrying...")
                continue

            score = data.get("score")
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = 1

            if score not in (0, 1, 2):
                score = 1

            note = data.get("note", "").strip()
            if not note:
                note = (
                    "Fully addressed the question with relevant content"
                    if score == 2
                    else "Partially addressed the question; some key aspects missing"
                    if score == 1
                    else "Response did not address the question"
                )

            return {"score": score, "note": note}

        except Exception as e:
            print(f"[COMPREHENSION] ERROR on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                return {"score": 1, "note": "Evaluation failed after retries"}

    return {"score": 1, "note": "Evaluation failed"}