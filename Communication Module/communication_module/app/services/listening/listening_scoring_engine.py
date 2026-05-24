"""
listening_scoring_engine.py  v3
────────────────────────────────
Continuous scoring for the listening module — no hard thresholds.

Pipeline:
  1. Collect raw signal values per parameter per clip
  2. Convert to continuous 0–1 scores
  3. Weighted average → 0–1
  4. Scale to 0–2, round to nearest 0.5
  5. Convert to /10

Listening weights:
  accuracy:       0.40
  retention:      0.30
  reconstruction: 0.30  (REPEAT clips only)
"""

PARAM_WEIGHTS = {
    "listening_accuracy":      0.40,
    "retention":               0.30,
    "comprehension":           0.30,
}
MAX_SUB = 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Normalise: 0–1 → 0–2, rounded to nearest 0.5
# ─────────────────────────────────────────────────────────────────────────────

def _norm(raw_0_1: float) -> float:
    scaled = max(0.0, min(1.0, raw_0_1)) * 2.0
    return round(round(scaled * 2) / 2, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Continuous signal → 0–1 per parameter
# ─────────────────────────────────────────────────────────────────────────────

def _accuracy_to_01(param: dict) -> float:
    """
    Inputs:
      score           → LLM integer 0–2 (primary, used as 0–1 base)
      keyword_hit_rate → 0–1 continuous signal
    """
    llm_base  = param.get("score", 1) / 2.0
    khr       = param.get("keyword_hit_rate", None)

    if khr is not None:
        # Blend: LLM score weighted 0.7, keyword signal 0.3
        return max(0.0, min(1.0, llm_base * 0.70 + float(khr) * 0.30))
    return max(0.0, min(1.0, llm_base))


def _retention_to_01(param: dict) -> float:
    """
    Inputs:
      score          → LLM integer 0–2
      coverage_ratio → token/fact coverage 0–1
    """
    llm_base = param.get("score", 1) / 2.0
    coverage = param.get("coverage_ratio", None)

    if coverage is not None:
        return max(0.0, min(1.0, llm_base * 0.60 + float(coverage) * 0.40))
    return max(0.0, min(1.0, llm_base))


def _comprehension_to_01(param: dict) -> float:
    """
    Inputs:
      score                → LLM integer 0–2
    """
    llm_base  = param.get("score", 1) / 2.0
    return max(0.0, min(1.0, llm_base))


# ─────────────────────────────────────────────────────────────────────────────
# Verdict / Strengths / Improvements
# ─────────────────────────────────────────────────────────────────────────────

def _verdict(score_10: int) -> str:
    if score_10 >= 9:   return "Excellent listening and comprehension skills"
    elif score_10 >= 7: return "Good listening ability with minor gaps"
    elif score_10 >= 5: return "Moderate listening — several areas to improve"
    elif score_10 >= 3: return "Below average listening comprehension"
    else:               return "Significant listening difficulties identified"


def _strengths(avgs_01: dict) -> list:
    out = []
    if avgs_01.get("listening_accuracy", 0) >= 0.70:
        out.append("Accurately captures spoken content and key details")
    elif avgs_01.get("listening_accuracy", 0) >= 0.45:
        out.append("Generally captures key information from audio")
    if avgs_01.get("retention", 0) >= 0.70:
        out.append("Strong ability to retain and recall full sentences")
    elif avgs_01.get("retention", 0) >= 0.45:
        out.append("Retains most of the spoken content")
    if avgs_01.get("comprehension", 0) >= 0.70:
        out.append("Demonstrates excellent understanding of complex questions")
    elif avgs_01.get("comprehension", 0) >= 0.45:
        out.append("Generally grasps the context of the audio passages")
    return out[:4] if out else ["Attempted all listening tasks"]


def _improvements(avgs_01: dict) -> list:
    out = []
    if avgs_01.get("listening_accuracy", 1) < 0.40:
        out.append("Focus on capturing key words, numbers, and names accurately")
    elif avgs_01.get("listening_accuracy", 1) < 0.65:
        out.append("Pay closer attention to specific details in the audio")
    if avgs_01.get("retention", 1) < 0.40:
        out.append("Practise recalling complete sentences rather than fragments")
    elif avgs_01.get("retention", 1) < 0.65:
        out.append("Work on retaining the full content of longer passages")
    if avgs_01.get("comprehension", 1) < 0.40:
        out.append("Focus on understanding the overall context rather than just facts")
    elif avgs_01.get("comprehension", 1) < 0.65:
        out.append("Try to improve contextual understanding of spoken narratives")
    return out[:4] if out else ["Continue practising listening exercises"]


# ─────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_listening_scores(clip_results: list) -> dict:
    """
    Aggregate continuous scores across all clip results.

    Key behaviour:
    - sentence_reconstruction only present in REPEAT clips.
      used_w dynamically tracks which params have data → correct normalisation.
    - All intermediate values remain continuous; rounding only at final stage.
    """
    param_01: dict[str, list] = {p: [] for p in PARAM_WEIGHTS}

    converters = {
        "listening_accuracy":      _accuracy_to_01,
        "retention":               _retention_to_01,
        "comprehension":           _comprehension_to_01,
    }

    for clip in clip_results:
        if not isinstance(clip, dict) or "error" in clip:
            param_01["listening_accuracy"].append(0.0)
            param_01["retention"].append(0.0)
            param_01["comprehension"].append(0.0)
            continue
            
        for param, fn in converters.items():
            raw = clip.get(param)
            if isinstance(raw, dict) and "score" in raw:
                param_01[param].append(fn(raw))
            else:
                param_01[param].append(0.0)

    # Average per parameter
    avgs_01: dict[str, float] = {}
    for param, vals in param_01.items():
        if vals:
            avgs_01[param] = round(sum(vals) / len(vals), 4)

    # Weighted sum (dynamic denominator)
    weighted_sum = 0.0
    used_w       = 0.0
    for param, weight in PARAM_WEIGHTS.items():
        if param in avgs_01:
            weighted_sum += avgs_01[param] * weight
            used_w       += weight

    if used_w == 0:
        return {
            "listening_score":    0.0,
            "listening_score_10": 0,
            "summary": {"verdict": "No data", "strengths": [], "improvements": []},
            "parameters":  {},
            "clip_details": clip_results,
        }

    # Normalise → 0–1, then scale → 0–2 (nearest 0.5)
    raw_01          = weighted_sum / used_w
    final_score     = _norm(raw_01)
    score_10        = int(round((final_score / MAX_SUB) * 10))

    # Parameter summary for frontend (continuous scores)
    param_summary = {}
    for param, vals in param_01.items():
        if vals:
            param_summary[param] = {
                "avg_score_01":  round(sum(vals) / len(vals), 3),
                "avg_score_02":  round(_norm(sum(vals) / len(vals)), 1),
                "clip_scores":   [round(v, 3) for v in vals],
            }

    return {
        "listening_score":    final_score,
        "listening_score_10": score_10,
        "summary": {
            "verdict":      _verdict(score_10),
            "strengths":    _strengths(avgs_01),
            "improvements": _improvements(avgs_01),
        },
        "parameters":  param_summary,
        "clip_details": clip_results,
        # Expose for debugging
        "_continuous_scores": {k: round(v, 3) for k, v in avgs_01.items()},
    }