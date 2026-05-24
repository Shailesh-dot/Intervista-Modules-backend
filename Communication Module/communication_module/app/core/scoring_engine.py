"""
scoring_engine.py  v2
──────────────────────
Implements industry-standard continuous scoring (no hard thresholds).

Pipeline per parameter:
  1. Extract features (done upstream in service layer)
  2. Convert features to continuous 0–1 scores
  3. Combine via weighted average → raw score 0–1
  4. Scale to 0–2
  5. Round ONLY at final stage to nearest 0.5

Final aggregation → /10 scale.
"""

import math

# ── Speaking weights ──────────────────────────────────────────────────────────
SPEAKING_WEIGHTS = {
    "pronunciation": 0.25,
    "fluency":       0.20,
    "tone":          0.15,
    "grammar":       0.20,
    "comprehension": 0.20,
}

MAX_SUB = 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Normalise helper: raw 0–1 → 0–2, rounded to nearest 0.5
# ─────────────────────────────────────────────────────────────────────────────

def _norm(raw_0_1: float) -> float:
    """Scale a 0–1 raw score to 0–2, rounded to nearest 0.5."""
    scaled = max(0.0, min(1.0, raw_0_1)) * 2.0
    return round(round(scaled * 2) / 2, 1)   # nearest 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Pronunciation — continuous signal computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_pronunciation_score(details: dict) -> float:
    """
    Inputs (from pronunciation_service):
      clarity          → seg_conf      (0–1)
      consistency      → word consistency (0–1)
      composite_score  → pre-computed composite (0–1)  [used as primary]
    Returns continuous 0–1 score.
    """
    composite   = details.get("composite_score", None)
    clarity     = details.get("clarity", 0.75)
    consistency = details.get("consistency", 0.75)

    if composite is not None:
        # composite already blends seg_conf + mean_prob + consistency - ns_penalty
        # Blend composite (primary) with raw signals for robustness
        raw = composite * 0.70 + clarity * 0.20 + consistency * 0.10
    else:
        raw = clarity * 0.55 + consistency * 0.45

    return max(0.0, min(1.0, raw))


# ─────────────────────────────────────────────────────────────────────────────
# Fluency — continuous signal computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_fluency_score(details: dict) -> float:
    """
    Inputs:
      wpm          → words per minute
      filler_rate  → filler words as % of total words
      pauses       → {"count": int, "avg_duration": float}
    Returns continuous 0–1 score.
    """
    wpm          = details.get("wpm", 130.0)
    filler_rate  = details.get("filler_rate", 0.0)
    pause_data   = details.get("pauses", {})
    avg_pause    = pause_data.get("avg_duration", 0.0)

    # WPM score: centred on 140 wpm, ±60 either side → 0 at <80 or >200
    wpm_score    = max(0.0, 1.0 - abs(wpm - 140.0) / 60.0)

    # Pause score: 0 pause → 1.0; 2+ s average → 0.0
    pause_score  = max(0.0, 1.0 - avg_pause / 2.0)

    # Filler score: 0% → 1.0; 15%+ → 0.0
    filler_score = max(0.0, 1.0 - filler_rate / 15.0)

    raw = (wpm_score * 0.40) + (pause_score * 0.30) + (filler_score * 0.30)
    return max(0.0, min(1.0, raw))


# ─────────────────────────────────────────────────────────────────────────────
# Tone — continuous signal computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_tone_score(details: dict) -> float:
    """
    Inputs:
      score            → legacy 0–2 integer (converted to 0–1)
      pitch_variation  → Hz std-dev  (higher = more expressive)
      energy_variation → amplitude variation (0–1 scale)
    Returns continuous 0–1 score.
    """
    # If tone_analyzer already provides a composite via diagnostics, prefer it
    diagnostics = details.get("diagnostics", {})
    composite   = diagnostics.get("composite", None)

    if composite is not None:
        return max(0.0, min(1.0, float(composite)))

    # Fallback: convert legacy integer score + analogue signals
    legacy     = details.get("score", 1)
    base       = legacy / 2.0  # 0 → 0.0, 1 → 0.5, 2 → 1.0

    pitch_var  = details.get("pitch_variation", 30.0)
    energy_var = details.get("energy_variation", 0.3)

    # Pitch: 0 Hz → 0.0; 60+ Hz variation → 1.0
    pitch_score  = max(0.0, min(1.0, pitch_var / 60.0))
    # Energy: moderate variation (0.3–0.5) is ideal; >0.8 penalised slightly
    energy_score = max(0.0, 1.0 - abs(energy_var - 0.4) / 0.6)

    raw = base * 0.50 + pitch_score * 0.30 + energy_score * 0.20
    return max(0.0, min(1.0, raw))


# ─────────────────────────────────────────────────────────────────────────────
# Grammar — continuous LLM score
# ─────────────────────────────────────────────────────────────────────────────

def _compute_grammar_score(details: dict) -> float:
    """
    LLM returns a float in {0, 0.5, 1.0, 1.5, 2.0}.
    Map directly to 0–1 by dividing by 2.
    Fallback: use mistake count if score key absent.
    """
    raw = details.get("score", None)
    if raw is not None:
        return max(0.0, min(1.0, float(raw) / 2.0))

    # Fallback from mistake count
    mistakes = len(details.get("mistakes", []))
    if mistakes == 0:
        return 1.0
    elif mistakes <= 1:
        return 0.75
    elif mistakes <= 3:
        return 0.50
    else:
        return max(0.0, 0.25 - (mistakes - 4) * 0.05)


# ─────────────────────────────────────────────────────────────────────────────
# Comprehension — continuous LLM score
# ─────────────────────────────────────────────────────────────────────────────

def _compute_comprehension_score(details: dict) -> float:
    """
    LLM returns:
      score      → 0, 1, or 2 (integer)
      relevance  → 0–1 (optional fine-grained)
      completeness → 0–1 (optional fine-grained)
    Returns continuous 0–1 score.
    """
    relevance    = details.get("relevance", None)
    completeness = details.get("completeness", None)

    if relevance is not None and completeness is not None:
        raw = float(relevance) * 0.60 + float(completeness) * 0.40
        return max(0.0, min(1.0, raw))

    # Fallback: integer score / 2
    score = details.get("score", 1)
    return max(0.0, min(1.0, float(score) / 2.0))


# ─────────────────────────────────────────────────────────────────────────────
# Verdict / Strengths / Improvements
# ─────────────────────────────────────────────────────────────────────────────

def _verdict(score_10: float) -> str:
    if score_10 >= 8.5:
        return "Excellent communication skills"
    elif score_10 >= 7.0:
        return "Good communication with minor improvements needed"
    elif score_10 >= 5.5:
        return "Moderate communication — several areas to improve"
    elif score_10 >= 4.0:
        return "Below average — focused improvement required"
    else:
        return "Significant communication challenges identified"


def _strengths(details: dict, scores_01: dict) -> list:
    """Generate strength bullets from continuous 0–1 scores."""
    out = []

    if scores_01.get("pronunciation", 0) >= 0.65:
        out.append("Clear and consistent pronunciation")
    elif scores_01.get("pronunciation", 0) >= 0.45:
        out.append("Generally understandable articulation")

    f  = details.get("fluency", {})
    fs = scores_01.get("fluency", 0)
    if fs >= 0.70:
        wpm = f.get("wpm", 0)
        if 120 <= wpm <= 155:
            out.append("Fluent and natural speaking pace")
        else:
            out.append("Good speaking rhythm overall")
    if f.get("filler_rate", 99) < 3:
        out.append("Minimal use of filler words")

    if scores_01.get("tone", 0) >= 0.65:
        out.append("Good vocal energy and engagement")
    elif scores_01.get("tone", 0) >= 0.45:
        out.append("Some vocal variety present")

    g = details.get("grammar", {})
    if scores_01.get("grammar", 0) >= 0.80:
        out.append("Strong grammar and sentence structure")
    elif scores_01.get("grammar", 0) >= 0.55 and len(g.get("mistakes", [])) <= 1:
        out.append("Mostly correct grammar")

    if scores_01.get("comprehension", 0) >= 0.75:
        out.append("Addressed the question thoroughly")
    elif scores_01.get("comprehension", 0) >= 0.45:
        out.append("Attempted to address the question")

    return out[:4] if out else ["Attempted all parts of the evaluation"]


def _improvements(details: dict, scores_01: dict) -> list:
    out = []

    SYSTEM_NOTES = {
        "no answer provided to evaluate", "no speech detected to evaluate",
        "evaluation failed", "could not evaluate comprehension",
        "no question provided for comprehension check",
    }

    p = details.get("pronunciation", {})
    if scores_01.get("pronunciation", 1) < 0.40:
        out.append("Work on pronunciation clarity and articulation")
    elif scores_01.get("pronunciation", 1) < 0.60:
        out.append("Improve consistency of articulation across words")

    f   = details.get("fluency", {})
    fs  = scores_01.get("fluency", 1)
    wpm = f.get("wpm", 130)
    if fs < 0.40:
        out.append("Adjust speaking pace — aim for 120–150 WPM")
    elif fs < 0.65:
        if f.get("filler_rate", 0) > 5:
            out.append("Reduce filler words (um, uh, basically, so)")
        if wpm < 110:
            out.append("Speak with more confidence and pace")
        elif wpm > 165:
            out.append("Slow down slightly for better clarity")
    if f.get("pauses", {}).get("count", 0) > 4:
        out.append("Reduce long pauses between sentences")

    t  = details.get("tone", {})
    ts = scores_01.get("tone", 1)
    if ts < 0.35:
        out.append("Add more vocal energy and expression")
    elif ts < 0.55:
        pv = t.get("pitch_variation", 99)
        ev = t.get("energy_variation", 0)
        if pv < 20:
            out.append("Vary pitch to sound less monotone")
        elif ev > 0.8:
            out.append("Maintain consistent volume throughout")

    g        = details.get("grammar", {})
    mistakes = g.get("mistakes", [])
    gs       = scores_01.get("grammar", 1)
    if gs < 0.35:
        out.append("Focus on basic sentence structure and grammar")
    elif gs < 0.65 and mistakes:
        first = mistakes[0]
        if isinstance(first, dict) and first.get("corrected"):
            out.append(
                f"Fix grammar — e.g. use \"{first['corrected']}\" not \"{first['original']}\""
            )
        else:
            out.append("Fix minor grammar mistakes")

    c      = details.get("comprehension", {})
    c_note = c.get("note", "").lower().strip()
    cs     = scores_01.get("comprehension", 1)
    if cs < 0.35 and c_note not in SYSTEM_NOTES:
        out.append("Make sure to directly answer the question asked")
    elif cs < 0.65:
        raw_note = c.get("note", "")
        if raw_note and raw_note.lower() not in SYSTEM_NOTES and len(raw_note) < 80:
            out.append(raw_note)
        elif raw_note.lower() not in SYSTEM_NOTES:
            out.append("Cover all parts of the question more thoroughly")

    return out[:4] if out else ["Continue practising interview responses"]


# ─────────────────────────────────────────────────────────────────────────────
# Main aggregator — single question
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_scores(**kwargs) -> dict:
    """
    Accepts keyword args matching SPEAKING_WEIGHTS keys.
    Each value is a details dict from the respective service.

    Steps:
      1. Compute continuous 0–1 score per parameter
      2. Weighted average → raw 0–1
      3. Scale to 0–2, round to 0.5
      4. Convert to /10
    """
    # No speech fast-path
    if all("No speech detected" in str(v.get("note", "")) for v in kwargs.values()):
        return {
            "final_score":    0.0,
            "final_score_10": 0,
            "summary": {
                "verdict":      "No speech detected",
                "strengths":    [],
                "improvements": ["Please ensure your microphone is working and speak clearly into it."],
            },
            "details": kwargs,
        }

    # ── Step 1: continuous 0–1 per parameter ─────────────────────────────────
    scorers = {
        "pronunciation": _compute_pronunciation_score,
        "fluency":       _compute_fluency_score,
        "tone":          _compute_tone_score,
        "grammar":       _compute_grammar_score,
        "comprehension": _compute_comprehension_score,
    }

    scores_01: dict[str, float] = {}
    for key, fn in scorers.items():
        if key in kwargs:
            scores_01[key] = fn(kwargs[key])

    # ── Step 2: weighted average (only over present parameters) ───────────────
    weighted_sum = 0.0
    used_weight  = 0.0
    for key, weight in SPEAKING_WEIGHTS.items():
        if key in scores_01:
            weighted_sum += scores_01[key] * weight
            used_weight  += weight

    if used_weight == 0:
        return {
            "final_score":    0.0,
            "final_score_10": 0,
            "summary": {"verdict": "No data", "strengths": [], "improvements": []},
            "details": kwargs,
        }

    raw_01 = weighted_sum / used_weight

    # ── Step 3: scale to 0–2, round to nearest 0.5 ───────────────────────────
    final_score = _norm(raw_01)

    # ── Step 4: /10 ──────────────────────────────────────────────────────────
    score_10    = round((final_score / MAX_SUB) * 10, 1)

    details = {k: kwargs[k] for k in SPEAKING_WEIGHTS if k in kwargs}

    return {
        "final_score":    final_score,
        "final_score_10": int(round(score_10)),
        "summary": {
            "verdict":      _verdict(score_10),
            "strengths":    _strengths(details, scores_01),
            "improvements": _improvements(details, scores_01),
        },
        "details": details,
        # Expose continuous scores for debugging / frontend charts
        "_continuous_scores": {k: round(v, 3) for k, v in scores_01.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Session aggregator — Speaking (3 questions → 1 overall result)
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_speaking_session(results: list) -> dict:
    """
    Receives a list of per-question evaluation results (from /evaluate).
    Averages continuous 0–1 scores across questions, then re-applies
    full aggregation so strengths / improvements are session-level.
    """
    if not results:
        return {
            "final_score": 0.0, "final_score_10": 0,
            "summary": {"verdict": "No data", "strengths": [], "improvements": []},
            "details": {},
        }

    scorers = {
        "pronunciation": _compute_pronunciation_score,
        "fluency":       _compute_fluency_score,
        "tone":          _compute_tone_score,
        "grammar":       _compute_grammar_score,
        "comprehension": _compute_comprehension_score,
    }

    # Collect continuous 0–1 scores per parameter across questions
    param_scores_01: dict[str, list] = {k: [] for k in scorers}
    param_details:   dict[str, list] = {k: [] for k in scorers}

    for r in results:
        if r.get("status") == "no_valid_speech" or "error" in r:
            for key in scorers:
                param_scores_01[key].append(0.0)
                param_details[key].append({"score": 0, "note": "No valid speech detected"})
            continue

        details = r.get("details", {})
        for key, fn in scorers.items():
            if key in details:
                param_scores_01[key].append(fn(details[key]))
                param_details[key].append(details[key])
            else:
                param_scores_01[key].append(0.0)
                param_details[key].append({"score": 0, "note": "No valid speech detected"})

    def _avg(lst): return sum(lst) / len(lst) if lst else None

    # Build averaged detail dicts so _strengths / _improvements work
    avg_details: dict = {}
    avg_scores_01: dict = {}

    for key in scorers:
        scores = param_scores_01[key]
        if not scores:
            continue
        avg_scores_01[key] = _avg(scores)

        # Merge representative details: average numeric fields
        sample = param_details[key][0].copy()
        numeric_keys = [k for k, v in sample.items() if isinstance(v, (int, float))]
        for nk in numeric_keys:
            vals = [d.get(nk, 0) for d in param_details[key] if isinstance(d.get(nk), (int, float))]
            if vals:
                sample[nk] = round(sum(vals) / len(vals), 3)

        # Collect all grammar mistakes (up to 3 total across questions)
        if key == "grammar":
            all_mistakes = []
            for d in param_details[key]:
                all_mistakes.extend(d.get("mistakes", []))
            sample["mistakes"] = all_mistakes[:3]

        avg_details[key] = sample

    # Weighted average of averaged 0–1 scores
    weighted_sum = 0.0
    used_weight  = 0.0
    for key, weight in SPEAKING_WEIGHTS.items():
        if key in avg_scores_01:
            weighted_sum += avg_scores_01[key] * weight
            used_weight  += weight

    if used_weight == 0:
        return {
            "final_score": 0.0, "final_score_10": 0,
            "summary": {"verdict": "No data", "strengths": [], "improvements": []},
            "details": {},
        }

    raw_01      = weighted_sum / used_weight
    final_score = _norm(raw_01)
    score_10    = round((final_score / MAX_SUB) * 10, 1)

    return {
        "final_score":    final_score,
        "final_score_10": int(round(score_10)),
        "summary": {
            "verdict":      _verdict(score_10),
            "strengths":    _strengths(avg_details, avg_scores_01),
            "improvements": _improvements(avg_details, avg_scores_01),
        },
        "details": avg_details,
        "_continuous_scores": {k: round(v, 3) for k, v in avg_scores_01.items()},
    }