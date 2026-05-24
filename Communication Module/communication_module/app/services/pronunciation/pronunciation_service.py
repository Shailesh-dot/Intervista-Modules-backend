"""
pronunciation_service.py  v3
─────────────────────────────
Fixes:
  1. Thresholds lowered for Indian English (score=2: >=0.65, score=1: >=0.42)
  2. OOV exclusion: proper nouns with prob < 0.15 excluded from clarity calc
  3. Renamed "confidence" → "composite_score" to prevent frontend field confusion
"""

import re
import statistics

OOV_THRESHOLD = 0.15   # words below this are likely proper nouns — exclude


def _signal_segment_confidence(segments: list) -> tuple:
    if not segments:
        return 0.75, 0.75
    logprobs = [s["avg_logprob"] for s in segments if "avg_logprob" in s]
    if not logprobs:
        return 0.75, 0.75
    avg_conf   = max(0.0, min(1.0, 1.0 + sum(logprobs) / len(logprobs)))
    worst_conf = max(0.0, min(1.0, 1.0 + min(logprobs)))
    return round(avg_conf, 3), round(worst_conf, 3)


def _signal_word_clarity(words: list) -> tuple:
    """
    OOV exclusion: skip words with probability < OOV_THRESHOLD.
    These are proper nouns/unknown words Whisper hasn't seen — they should
    not penalise the candidate's actual pronunciation quality.
    """
    if not words:
        return 0.80, 0.75
    all_probs = [w["probability"] for w in words
                 if "probability" in w and w.get("word", "").strip()]
    if not all_probs:
        return 0.80, 0.75

    probs = [p for p in all_probs if p >= OOV_THRESHOLD]
    if len(probs) < max(1, len(all_probs) * 0.3):
        probs = all_probs   # fallback if almost everything OOV

    mean_p     = statistics.mean(probs)
    std_p      = statistics.stdev(probs) if len(probs) > 1 else 0.0
    weak_ratio = sum(1 for p in probs if p < 0.70) / len(probs)
    consistency = max(0.0, mean_p - std_p * 0.5 - weak_ratio * 0.3)
    return round(mean_p, 3), round(consistency, 3)


def _signal_no_speech_penalty(segments: list) -> float:
    if not segments:
        return 0.0
    ns  = [s.get("no_speech_prob", 0.0) for s in segments]
    avg = sum(ns) / len(ns)
    hi  = sum(1 for p in ns if p > 0.4)
    return round(min(0.3, avg * 0.5 + (hi / max(len(ns), 1)) * 0.2), 3)


def evaluate_pronunciation(
    expected_text:    str,
    spoken_text:      str,
    whisper_segments: list = None,
    whisper_words:    list = None,
) -> dict:
    segments = whisper_segments or []
    words    = whisper_words    or []

    seg_conf, worst_conf   = _signal_segment_confidence(segments)
    mean_prob, consistency = _signal_word_clarity(words)
    ns_penalty             = _signal_no_speech_penalty(segments)

    composite = (
        seg_conf    * 0.40 +
        mean_prob   * 0.35 +
        consistency * 0.15
    ) - ns_penalty * 0.10
    composite = round(max(0.0, min(1.0, composite)), 3)

    # Indian English calibrated thresholds (lowered from 0.80/0.60)
    if composite >= 0.60:
        score = 2
    elif composite >= 0.40:
        score = 1
    else:
        score = 0

    if worst_conf < 0.35 and score == 2:
        score = 1

    note = ("Speech is clear and understandable" if score == 2
            else "Mostly clear with some inconsistent articulation" if score == 1 and consistency < 0.65
            else "Understandable with mild accent variation" if score == 1
            else "Pronunciation needs significant improvement")

    return {
        "score":           score,
        "clarity":         seg_conf,
        "consistency":     consistency,
        "composite_score": composite,   # renamed from "confidence" to avoid frontend confusion
        "note":            note,
    }