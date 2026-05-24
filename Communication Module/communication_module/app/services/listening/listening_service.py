"""
listening_service.py  v2
─────────────────────────
ONE LLM call evaluates all 4 clips (accuracy + retention + reconstruction) together.

Old system: 2 REPEAT clips × 3 LLM calls + 2 QnA clips × 1 LLM call = 8 calls
New system: 1 combined LLM call for entire session                    = 1 call

Signal computation (keyword hit-rate, token coverage, edit-distance) runs locally
first and is passed into the single LLM call as anchors — same accuracy as before.

Parameters:
  1. listening_accuracy       — correct content captured?      (keyword + LLM)
  2. retention                — how complete was the recall?   (coverage ratio + LLM)
  3. comprehension            — did they understand the context? (LLM)
"""

import re
import json
import os
import statistics
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _tokens(text: str) -> set:
    STOP = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "is", "are", "was", "were", "be", "i", "you", "we", "it",
            "this", "that", "have", "has", "will", "please", "all", "can", "your"}
    return {w for w in _clean(text).split() if w and w not in STOP}


def _is_empty(text: str) -> bool:
    return not text or len(text.strip()) < 3


# ─────────────────────────────────────────────────────────────────────────────
# Clip-repeat detection  (QnA clips only)
# ─────────────────────────────────────────────────────────────────────────────

def _jaccard(text_a: str, text_b: str) -> float:
    a = _tokens(text_a)
    b = _tokens(text_b)
    if not a and not b:
        return 0.0
    return round(len(a & b) / max(len(a | b), 1), 3)


def _is_clip_repeat(reference: str, response: str, threshold: float = 0.50) -> bool:
    return _jaccard(reference, response) > threshold


# ─────────────────────────────────────────────────────────────────────────────
# Signal computation  (all pure Python — no network calls)
# ─────────────────────────────────────────────────────────────────────────────

def _keyword_hit_rate(key_facts: list, response: str) -> float:
    if not key_facts:
        return 0.75
    resp_lower = _clean(response)
    hits = sum(1 for kf in key_facts if _clean(kf) in resp_lower)
    return round(hits / len(key_facts), 2)


def _token_coverage(reference: str, response: str) -> float:
    ref_tokens  = _tokens(reference)
    resp_tokens = _tokens(response)
    if not ref_tokens:
        return 0.75
    return round(len(ref_tokens & resp_tokens) / len(ref_tokens), 2)


def _edit_distance(a: list, b: list) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _structure_similarity(reference: str, response: str) -> float:
    ref  = _clean(reference).split()
    resp = _clean(response).split()
    if not ref:
        return 0.75
    dist = _edit_distance(ref, resp)
    return round(max(0.0, 1.0 - dist / max(len(ref), 1)), 2)


# ─────────────────────────────────────────────────────────────────────────────
# LLM helper
# ─────────────────────────────────────────────────────────────────────────────

def _llm(prompt: str, max_tokens: int = 1000) -> dict:
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            raw     = resp.choices[0].message.content
            cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if m:
                    return json.loads(m.group())
        except Exception as e:
            if attempt == 2:
                print(f"LLM ERROR: {e}")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Combined prompt — evaluates all clips in one shot
# ─────────────────────────────────────────────────────────────────────────────

COMBINED_LISTENING_PROMPT = """You are a listening comprehension evaluator. Evaluate ALL clips in a single pass using the pre-computed signals provided as anchors.

SCORING RULES:
- Use the pre-computed signals (keyword_hit_rate, fact_coverage) as primary anchors
- Only override if you detect clear semantic mismatch the numbers cannot capture
- Bias TOWARDS higher scores when in doubt — do NOT be overly strict

SCORE SCALE (per parameter): 0 | 1 | 2

LISTENING ACCURACY:
  2 = ≥70% key facts captured AND content is correct
  1 = 30–69% OR 1–2 minor errors
  0 = <30% OR major factual errors OR no answer

RETENTION:
  2 = ≥70% token/fact coverage — full or near-full recall
  1 = 30–69% — roughly half recalled
  0 = <30% — major portions missing

COMPREHENSION:
  2 = Excellent understanding of the question and its relation to the reference passage
  1 = Partial understanding; answer is somewhat relevant but misses the core implication
  0 = Completely misses the point of the question, or no answer

---

CLIPS TO EVALUATE:

{clip_blocks}

---

Return ONLY valid JSON — no markdown, no explanation:

{{
  "clips": [
    {{
    {
      "clip_id": "<clip_id>",
      "task_type": "<REPEAT|QnA>",
      "listening_accuracy": {
        "score": <0|1|2>,
        "note": "<max 15 words>"
      },
      "retention": {
        "score": <0|1|2>,
        "note": "<max 15 words>"
      },
      "comprehension": {
        "score": <0|1|2>,
        "note": "<max 15 words>"
      }
    }
  ]
}

For each QnA clip, listening_accuracy, retention, and comprehension scores should reflect the quality of the answer to the provided question. Output one object per clip in the same order as the input.
"""


def _build_clip_block(clip_id: str, task_type: str, clip_signals: dict) -> str:
    """Format a single clip's signals into the prompt block."""
    lines = [f"CLIP: {clip_id}  (type: {task_type})"]

    if task_type == "REPEAT":
        lines.append(f"  Reference:          \"{clip_signals['reference']}\"")
        lines.append(f"  Candidate response: \"{clip_signals['transcript']}\"")
        lines.append(f"  keyword_hit_rate:      {clip_signals['keyword_hit_rate']:.0%}")
        lines.append(f"  token_coverage:        {clip_signals['token_coverage']:.0%}")
        lines.append(f"  structure_similarity:  {clip_signals['structure_similarity']:.0%}")

    elif task_type == "QnA":
        lines.append(f"  Reference passage: \"{clip_signals['reference']}\"")
        qa = clip_signals.get("q1", {})
        lines.append(f"  Q1: {qa.get('question', '')}")
        lines.append(f"    Answer:            \"{qa.get('answer', '[no answer]')}\"")
        lines.append(f"    keyword_hit_rate:  {qa.get('keyword_hit_rate', 0.0):.0%}")
        lines.append(f"    fact_coverage:     {qa.get('fact_coverage', 0.0):.0%}")
        if qa.get("flagged_as_repeat"):
            lines.append(f"    ⚠ flagged as clip repeat — penalise this answer")
        if qa.get("flagged_as_empty"):
            lines.append(f"    ⚠ no answer provided")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Penalty dicts
# ─────────────────────────────────────────────────────────────────────────────

EMPTY_PENALTY = {
    "score": 0,
    "note": "No response provided",
    "flagged_as_empty": True,
}

CLIP_REPEAT_PENALTY = {
    "score": 0,
    "note": "Candidate repeated the audio clip instead of answering the question",
    "flagged_as_repeat": True,
}


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluator — one LLM call for ALL clips
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_all_responses(session_clips: list, clip_responses: list) -> list:
    """
    Evaluate all clip responses in a single LLM call.

    session_clips   : list of ListeningClip objects
    clip_responses  : list of response dicts (same format as before)

    Returns list of result dicts, one per clip.
    """
    clip_map = {c.clip_id: c for c in session_clips}

    # ── Step 1: Compute all signals locally (no network) ─────────────────────
    clip_signals_list = []    # list of (clip_id, task_type, signals_dict)
    early_results     = {}    # clip_id → result if fully handled without LLM

    for resp in clip_responses:
        clip_id = resp["clip_id"]
        clip    = clip_map.get(clip_id)
        if not clip:
            early_results[clip_id] = {"clip_id": clip_id, "error": "Clip not found in session"}
            continue

        if clip.task_type == "REPEAT":
            transcript = resp.get("transcript", "")

            if _is_empty(transcript):
                early_results[clip_id] = {
                    "clip_id":                clip_id,
                    "task_type":              "REPEAT",
                    "transcript":             transcript,
                    "listening_accuracy":     {**EMPTY_PENALTY, "keyword_hit_rate": 0.0},
                    "retention":              {**EMPTY_PENALTY, "coverage_ratio": 0.0},
                    "comprehension":          {**EMPTY_PENALTY},
                }
                print(f"[{clip_id}] REPEAT — empty transcript, all params scored 0")
                continue

            khr        = _keyword_hit_rate(clip.key_facts, transcript)
            cov        = _token_coverage(clip.reference_text, transcript)
            sim        = _structure_similarity(clip.reference_text, transcript)

            clip_signals_list.append((clip_id, "REPEAT", {
                "reference":            clip.reference_text,
                "transcript":           transcript,
                "keyword_hit_rate":     khr,
                "token_coverage":       cov,
                "structure_similarity": sim,
            }))

        elif clip.task_type == "QnA":
            a1 = resp.get("answer_q1", "")
            kf  = clip.key_facts
            kf1 = kf[0] if len(kf) > 0 else []

            repeat_q1 = (not _is_empty(a1)) and _is_clip_repeat(clip.reference_text, a1)

            # If answer is empty
            if _is_empty(a1):
                early_results[clip_id] = {
                    "clip_id":            clip_id,
                    "task_type":          "QnA",
                    "listening_accuracy": {**EMPTY_PENALTY, "q1": EMPTY_PENALTY,
                                           "score": 0},
                    "retention":          {**EMPTY_PENALTY, "q1": EMPTY_PENALTY,
                                           "score": 0},
                    "comprehension":      {**EMPTY_PENALTY, "q1": EMPTY_PENALTY,
                                           "score": 0},
                }
                continue

            q1_signals = {
                "question":         clip.questions[0] if clip.questions else "",
                "answer":           a1 if not _is_empty(a1) else "[no answer]",
                "keyword_hit_rate": 0.0 if _is_empty(a1) else _keyword_hit_rate(kf1, a1),
                "fact_coverage":    0.0 if _is_empty(a1) else _keyword_hit_rate(kf1, a1),
                "flagged_as_repeat": repeat_q1,
                "flagged_as_empty":  _is_empty(a1),
            }

            clip_signals_list.append((clip_id, "QnA", {
                "reference": clip.reference_text,
                "q1":        q1_signals,
            }))

    # ── Step 2: Single combined LLM call ─────────────────────────────────────
    llm_results_map: dict[str, dict] = {}

    if clip_signals_list:
        clip_blocks = "\n\n".join(
            _build_clip_block(cid, tt, sigs)
            for cid, tt, sigs in clip_signals_list
        )
        prompt = COMBINED_LISTENING_PROMPT.replace("{clip_blocks}", clip_blocks)
        llm_data = _llm(prompt, max_tokens=1200)

        for item in llm_data.get("clips", []):
            cid = item.get("clip_id", "")
            if cid:
                llm_results_map[cid] = item

    # ── Step 3: Assemble final results ────────────────────────────────────────
    results = []
    for resp in clip_responses:
        clip_id = resp["clip_id"]

        # Use pre-computed early result if available
        if clip_id in early_results:
            results.append(early_results[clip_id])
            continue

        clip   = clip_map.get(clip_id)
        llm    = llm_results_map.get(clip_id, {})
        result = {"clip_id": clip_id, "task_type": clip.task_type if clip else "UNKNOWN"}

        # Find signals for this clip
        sigs = next((s for cid, tt, s in clip_signals_list if cid == clip_id), {})

        if clip and clip.task_type == "REPEAT":
            transcript = resp.get("transcript", "")
            result["transcript"] = transcript
            result["reference_text"] = clip.reference_text
            result["key_facts"] = clip.key_facts

            # Accuracy
            acc_llm  = llm.get("listening_accuracy", {})
            acc_score = _anchored_score(
                llm_score  = acc_llm.get("score"),
                signal_val = sigs.get("keyword_hit_rate", 0.5),
                low=0.30, high=0.85,
            )
            result["listening_accuracy"] = {
                "score":            acc_score,
                "keyword_hit_rate": sigs.get("keyword_hit_rate", 0.0),
                "note":             acc_llm.get("note", ""),
            }

            # Retention
            ret_llm  = llm.get("retention", {})
            ret_score = _anchored_score(
                llm_score  = ret_llm.get("score"),
                signal_val = sigs.get("token_coverage", 0.5),
                low=0.35, high=0.75,
            )
            result["retention"] = {
                "score":          ret_score,
                "coverage_ratio": sigs.get("token_coverage", 0.0),
                "note":           ret_llm.get("note", ""),
            }

            # Comprehension
            comp_llm  = llm.get("comprehension", {})
            comp_score = _safe_score(comp_llm.get("score"), default=1)
            
            result["comprehension"] = {
                "score": comp_score,
                "note":  comp_llm.get("note", ""),
            }

            print(
                f"[{clip_id}] REPEAT | "
                f"accuracy={acc_score} retention={ret_score} comprehension={comp_score}"
            )

        elif clip and clip.task_type == "QnA":
            kf  = clip.key_facts
            kf1 = kf[0] if len(kf) > 0 else []
            a1  = resp.get("answer_q1", "")

            q1_sigs = sigs.get("q1", {})

            # Per-question accuracy and retention (from LLM aggregate)
            acc_llm   = llm.get("listening_accuracy", {})
            ret_llm   = llm.get("retention", {})
            comp_llm  = llm.get("comprehension", {})

            acc_score  = _safe_score(acc_llm.get("score"), default=1)
            ret_score  = _safe_score(ret_llm.get("score"), default=1)
            comp_score = _safe_score(comp_llm.get("score"), default=1)

            # Override with 0 if both answers penalised
            if q1_sigs.get("flagged_as_repeat"):
                acc_score  = 0
                ret_score  = 0
                comp_score = 0

            result["reference_text"] = clip.reference_text
            result["transcript"] = a1
            result["key_facts"] = kf1
            result["answers"] = {
                "q1": {
                    "question":          clip.questions[0] if clip.questions else "",
                    "transcript":        a1,
                    "expected_facts":    kf1,
                    "flagged_as_repeat": q1_sigs.get("flagged_as_repeat", False),
                    "flagged_as_empty":  q1_sigs.get("flagged_as_empty",  False),
                }
            }
            result["listening_accuracy"] = {
                "score": acc_score,
                "note":  acc_llm.get("note", ""),
            }
            result["retention"] = {
                "score": ret_score,
                "note":  ret_llm.get("note", ""),
            }
            result["comprehension"] = {
                "score": comp_score,
                "note":  comp_llm.get("note", ""),
            }

            print(
                f"[{clip_id}] QnA | accuracy={acc_score} retention={ret_score} comprehension={comp_score} | "
                f"expected_facts: {kf1}"
            )

        results.append(result)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_score(val, default: int = 1) -> int:
    try:
        s = int(val)
        return max(0, min(2, s))
    except (TypeError, ValueError):
        return default


def _anchored_score(
    llm_score,
    signal_val: float,
    low: float,
    high: float,
) -> int:
    """
    Use signal_val as a hard anchor when LLM would contradict it strongly.
    low  = threshold below which score=2 is forced down to 1
    high = threshold above which score=0 is forced up to 1
    """
    score = _safe_score(llm_score, default=1)
    if signal_val < low  and score == 2: score = 1
    if signal_val > high and score == 0: score = 1
    return score