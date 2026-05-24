"""
tone_analyzer.py  —  Advanced Tone Analyser  v2
─────────────────────────────────────────────────
Evaluates whether a speaker sounds engaged/expressive, neutral, or flat.
Focuses purely on vocal variation — not pronunciation, accent, or voice quality.

5 features:
  1. Pitch range      — normalized (p90-p10)/median
  2. Pitch movement   — mean(abs(diff(f0)))
  3. Energy dynamics  — RMS CV on voiced frames only (median-filtered)
  4. Pause pattern    — natural vs rushed vs hesitant (Whisper timestamps)
  5. Emphasis         — coordinated pitch+energy z-score peaks
  +  Jitter penalty   — voice instability deduction

Composite formula (spec):
  composite = 0.30*pitch_range + 0.20*movement + 0.20*energy
            + 0.15*pause + 0.10*emphasis - 0.05*jitter_penalty

Returns:
  score            int 0/1/2          pipeline key (unchanged)
  pitch_variation  float              backward-compat display key
  energy_variation float              backward-compat display key
  note             str                backward-compat display key
  tone_level       "Flat"|"Moderate"|"Expressive"
  strengths        list[str]
  issues           list[str]
  diagnostics      dict               all raw values for debugging
"""

import librosa
import numpy as np
import tempfile
import os
from pydub import AudioSegment

try:
    from scipy.ndimage import median_filter as _scipy_median
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ─────────────────────────────────────────────────────────────────────────────
# Audio loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_clean_audio(audio_file):
    audio_file.file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_file.file.read())
        raw = f.name
    clean = raw + "_clean.wav"
    seg = AudioSegment.from_file(raw).set_frame_rate(16000).set_channels(1)
    seg.export(clean, format="wav")
    y, sr = librosa.load(clean, sr=16000)
    return librosa.util.normalize(y), sr, raw, clean
        

# ─────────────────────────────────────────────────────────────────────────────
# Feature 1 + 5 — Pitch features (range, movement, jitter)
# ─────────────────────────────────────────────────────────────────────────────

def _pitch_features(y: np.ndarray, sr: int) -> tuple[dict, np.ndarray, np.ndarray]:
    """
    Extract F0 using pyin, remove NaN (unvoiced) frames.

    pitch_range   = (p90 - p10) / median_f0
                    Normalised so it is independent of absolute pitch level.
                    Fair for both male and female voices, and for Indian English
                    speakers whose baseline pitch differs from Western norms.

    movement_rate = mean(|diff(f0_clean)|)
                    Average Hz change between consecutive voiced frames.
                    High = dynamic, low = monotone.

    jitter        = movement_rate / mean(f0_clean)   [spec formula]
                    Normalized instability. Some jitter is natural;
                    only high values indicate nervous/unstable voice.
    """
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
    )

    voiced_ratio = float(np.sum(voiced_flag) / max(len(voiced_flag), 1))
    f0_clean = f0[~np.isnan(f0)]

    if len(f0_clean) < 5:
        return {
            "pitch_range":   0.0,
            "movement_rate": 0.0,
            "median_f0":     150.0,
            "voiced_ratio":  voiced_ratio,
            "jitter":        0.0,
            "pitch_std":     0.0,
        }

    p10       = float(np.percentile(f0_clean, 10))
    p90       = float(np.percentile(f0_clean, 90))
    median_f0 = float(np.median(f0_clean))
    pitch_std = float(np.std(f0_clean))

    pitch_range   = (p90 - p10) / max(median_f0, 1.0)
    movement_rate = float(np.mean(np.abs(np.diff(f0_clean))))
    jitter        = movement_rate / max(float(np.mean(f0_clean)), 1.0)

    return {
        "pitch_range":   round(pitch_range, 4),
        "movement_rate": round(movement_rate, 3),
        "median_f0":     round(median_f0, 1),
        "voiced_ratio":  round(voiced_ratio, 3),
        "jitter":        round(jitter, 4),
        "pitch_std":     round(pitch_std, 2),
    }, f0, voiced_flag


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2 — Energy dynamics
# ─────────────────────────────────────────────────────────────────────────────

def _energy_features(y: np.ndarray) -> dict:
    """
    RMS energy → median-filtered (5 frames ≈ 23 ms) to remove noise spikes
    → silence removed (< 20% of max) → CV on voiced frames only.

    Voiced-only CV is a cleaner signal than full-signal CV which is
    dominated by the silence/speech contrast rather than expressiveness.
    """
    energy = librosa.feature.rms(y=y)[0]

    if _HAS_SCIPY:
        smoothed = _scipy_median(energy.astype(float), size=5)
    else:
        smoothed = np.array([
            np.median(energy[max(0, i - 2): i + 3])
            for i in range(len(energy))
        ], dtype=float)

    threshold     = 0.20 * float(np.max(smoothed))
    voiced_energy = smoothed[smoothed > threshold]

    if len(voiced_energy) < 3:
        return {"energy_cv": 0.30, "energy_mean": 0.0}

    cv = float(np.std(voiced_energy) / max(np.mean(voiced_energy), 1e-6))
    return {
        "energy_cv":   round(cv, 4),
        "energy_mean": round(float(np.mean(voiced_energy)), 5),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3 — Pause analysis
# ─────────────────────────────────────────────────────────────────────────────

def _pause_features(segments: list, audio_duration: float) -> dict:
    """
    Gaps > 0.15s between consecutive Whisper segments are counted as pauses.

    Natural interview delivery:
      avg_pause 0.25–0.65s, rate 0.3–1.0 pauses/second

    Pause score 0–1 (used directly in composite):
      natural   → 1.0
      acceptable → 0.7
      slight issue → 0.5–0.55
      rushed/hesitant → 0.25–0.30
    """
    if not segments or len(segments) < 2:
        return {
            "pause_count":    0,
            "avg_pause_secs": 0.0,
            "pause_rate":     0.0,
            "pause_score":    0.6,
            "pause_label":    "unknown",
        }

    gaps = [
        float(segments[i].get("start", 0)) - float(segments[i - 1].get("end", 0))
        for i in range(1, len(segments))
    ]
    gaps = [g for g in gaps if g > 0.15]

    speech_dur  = max(audio_duration, 1.0)
    pause_count = len(gaps)
    avg_pause   = float(np.mean(gaps)) if gaps else 0.0
    pause_rate  = pause_count / speech_dur

    if pause_count == 0:
        score, label = 0.25, "rushed"
    elif avg_pause > 1.2 or pause_rate > 1.8:
        score, label = 0.30, "hesitant"
    elif avg_pause > 0.8 or pause_rate > 1.2:
        score, label = 0.55, "slightly hesitant"
    elif avg_pause < 0.20 or pause_rate < 0.25:
        score, label = 0.50, "slightly rushed"
    elif 0.25 <= avg_pause <= 0.65 and 0.3 <= pause_rate <= 1.0:
        score, label = 1.00, "natural"
    else:
        score, label = 0.70, "acceptable"

    return {
        "pause_count":    pause_count,
        "avg_pause_secs": round(avg_pause, 3),
        "pause_rate":     round(pause_rate, 3),
        "pause_score":    round(score, 3),
        "pause_label":    label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 4 — Emphasis detection
# ─────────────────────────────────────────────────────────────────────────────

def _emphasis_features(y: np.ndarray, sr: int, f0: np.ndarray, voiced_flag: np.ndarray) -> dict:
    """
    A frame is 'emphasized' when both pitch z-score > 1.5 AND energy z-score > 1.5.
    Catches stressed syllables and key-word emphasis simultaneously.
    Unvoiced frames are zeroed out so they never trigger emphasis.

    emphasis_ratio = mean(emphasis_mask)
    Natural expressive speech: 5–20% of frames.
    """
    energy = librosa.feature.rms(y=y)[0]
    if len(energy) < 3:
        return {"emphasis_ratio": 0.05, "emphasis_count": 0}

    e_z = (energy - np.mean(energy)) / max(np.std(energy), 1e-6)

    # f0 and voiced_flag are now passed directly to save CPU time

    f0_safe  = np.where(np.isnan(f0), 0.0, f0)
    f0_voiced = f0_safe[voiced_flag]
    if len(f0_voiced) < 3:
        return {"emphasis_ratio": 0.05, "emphasis_count": 0}

    f0_mean = np.mean(f0_voiced)
    f0_std  = max(np.std(f0_voiced), 1e-6)
    f0_z    = (f0_safe - f0_mean) / f0_std
    f0_z[~voiced_flag] = 0.0

    n              = min(len(f0_z), len(e_z))
    emphasis_mask  = (f0_z[:n] > 1.5) & (e_z[:n] > 1.5)
    emphasis_ratio = float(np.mean(emphasis_mask))

    return {
        "emphasis_ratio": round(emphasis_ratio, 4),
        "emphasis_count": int(np.sum(emphasis_mask)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sub-score normalisers (0.0 – 1.0)
# ─────────────────────────────────────────────────────────────────────────────

def _s_pitch_range(v: float) -> float:
    """< 0.12 → 0.0 | 0.12–0.25 → 0.5 | ≥ 0.25 → 1.0"""
    return 0.0 if v < 0.12 else (0.5 if v < 0.25 else 1.0)


def _s_movement(v: float) -> float:
    """< 5 Hz/f → 0.0 | 5–15 → 0.5 | ≥ 15 → 1.0"""
    return 0.0 if v < 5.0 else (0.5 if v < 15.0 else 1.0)


def _s_energy(v: float) -> float:
    """< 0.20 → 0.0 | 0.20–0.30 → 0.5 | 0.30–0.70 → 1.0 | > 0.70 → 0.5"""
    if v < 0.20:   return 0.0
    if v < 0.30:   return 0.5
    if v <= 0.70:  return 1.0
    return 0.5


def _s_emphasis(v: float) -> float:
    """< 0.02 → 0.0 | 0.02–0.05 → 0.5 | 0.05–0.25 → 1.0 | > 0.25 → 0.7"""
    if v < 0.02:   return 0.0
    if v < 0.05:   return 0.5
    if v <= 0.25:  return 1.0
    return 0.7


def _s_jitter(v: float) -> float:
    """Penalty: < 0.08 → 0.0 | 0.08–0.15 → 0.5 | ≥ 0.15 → 1.0"""
    return 0.0 if v < 0.08 else (0.5 if v < 0.15 else 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Feedback generator
# ─────────────────────────────────────────────────────────────────────────────

def _feedback(
    pitch_range: float,
    movement_rate: float,
    energy_cv: float,
    pause_label: str,
    emphasis_ratio: float,
    jitter: float,
    tone_level: str,
) -> tuple:
    strengths, issues = [], []

    if pitch_range >= 0.30:
        strengths.append("Good pitch variation — voice sounds expressive and engaging")
    elif pitch_range >= 0.20:
        strengths.append("Reasonable pitch variation across the response")
    else:
        issues.append("Pitch is quite flat — vary it more to emphasise key points")

    if movement_rate >= 20:
        strengths.append("Dynamic pitch movement — keeps the listener engaged")
    elif movement_rate < 8:
        issues.append("Pitch movement is low — speech sounds monotone at times")

    if 0.35 <= energy_cv <= 0.65:
        strengths.append("Consistent vocal energy with natural loudness variation")
    elif energy_cv < 0.25:
        issues.append("Vocal energy is very uniform — emphasise key words more")
    elif energy_cv > 0.75:
        issues.append("Volume is inconsistent — aim for steadier energy levels")

    if pause_label == "natural":
        strengths.append("Natural pausing rhythm — well-paced delivery")
    elif pause_label in ("rushed", "slightly rushed"):
        issues.append("Speech is slightly rushed — use short pauses to let ideas land")
    elif pause_label in ("hesitant", "slightly hesitant"):
        issues.append("Too many long pauses — practise to reduce hesitation gaps")

    if 0.06 <= emphasis_ratio <= 0.20:
        strengths.append("Good use of emphasis — key words stand out clearly")
    elif emphasis_ratio < 0.03:
        issues.append("No clear emphasis detected — stress important words more")

    if jitter > 0.15:
        issues.append("Voice sounds slightly unsteady — speak with more confidence")

    return strengths[:3], issues[:3]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyze_tone(audio_file, whisper_segments: list = None) -> dict:
    """
    Analyse tone/expressiveness of speech.

    Args:
        audio_file        : FastAPI UploadFile
        whisper_segments  : transcript_data["timestamps"] from whisper_service
                            Optional — pause analysis is skipped if not provided

    Returns dict with all original keys (score, pitch_variation,
    energy_variation, note) plus tone_level, strengths, issues, diagnostics.
    The pipeline and scoring_engine need no changes.
    """
    raw_path = clean_path = None
    try:
        y, sr, raw_path, clean_path = _load_clean_audio(audio_file)

        if len(y) == 0:
            raise ValueError("Empty audio after conversion")

        dur = librosa.get_duration(y=y, sr=sr)

        # ── 5 features ────────────────────────────────────────────────────────
        pf, f0, voiced_flag = _pitch_features(y, sr)
        ef  = _energy_features(y)
        psf = _pause_features(whisper_segments or [], dur)
        emf = _emphasis_features(y, sr, f0, voiced_flag)

        pitch_range    = pf["pitch_range"]
        movement_rate  = pf["movement_rate"]
        energy_cv      = ef["energy_cv"]
        pause_score    = psf["pause_score"]
        emphasis_ratio = emf["emphasis_ratio"]
        jitter         = pf["jitter"]

        # ── Sub-scores (0–1) ──────────────────────────────────────────────────
        pr_s  = _s_pitch_range(pitch_range)
        mr_s  = _s_movement(movement_rate)
        en_s  = _s_energy(energy_cv)
        em_s  = _s_emphasis(emphasis_ratio)
        ji_p  = _s_jitter(jitter)

        # ── Composite (spec formula) ──────────────────────────────────────────
        composite = (
            0.30 * pr_s  +
            0.20 * mr_s  +
            0.20 * en_s  +
            0.15 * pause_score +
            0.10 * em_s  -
            0.05 * ji_p
        )
        composite = round(max(0.0, min(1.0, composite)), 4)

        # ── Map to 0/1/2 for pipeline ─────────────────────────────────────────
        # 0.65+ → 2 Expressive | 0.40+ → 1 Moderate | else 0 Flat
        # Thresholds lowered vs standard to be fair to Indian English speakers
        if composite >= 0.65:
            score, tone_level = 2, "Expressive"
        elif composite >= 0.40:
            score, tone_level = 1, "Moderate"
        else:
            score, tone_level = 0, "Flat"

        # ── Feedback ──────────────────────────────────────────────────────────
        strengths, issues = _feedback(
            pitch_range, movement_rate, energy_cv,
            psf["pause_label"], emphasis_ratio, jitter, tone_level,
        )

        # ── Note (backward compat) ────────────────────────────────────────────
        if score == 2:
            note = "Good vocal variation and engagement"
        elif score == 1:
            note = ("Voice sounds monotone — try varying your pitch"
                    if pitch_range < 0.20
                    else "Moderate vocal expression — can be more engaging")
        else:
            note = "Tone is flat and lacks energy"

        return {
            # Pipeline-compatible (unchanged keys)
            "score":            score,
            "pitch_variation":  pf["pitch_std"],
            "energy_variation": round(energy_cv, 2),
            "note":             note,
            # Enriched output
            "tone_level":  tone_level,
            "strengths":   strengths,
            "issues":      issues,
            "diagnostics": {
                "pitch_range":    pitch_range,
                "movement_rate":  movement_rate,
                "median_f0":      pf["median_f0"],
                "energy_cv":      energy_cv,
                "emphasis_ratio": emphasis_ratio,
                "jitter":         jitter,
                "voiced_ratio":   pf["voiced_ratio"],
                "pause_count":    psf["pause_count"],
                "avg_pause_secs": psf["avg_pause_secs"],
                "pause_label":    psf["pause_label"],
                "composite":      composite,
                "sub_scores": {
                    "pitch_range":    pr_s,
                    "movement_rate":  mr_s,
                    "energy":         en_s,
                    "pause":          pause_score,
                    "emphasis":       em_s,
                    "jitter_penalty": ji_p,
                },
            },
        }

    except Exception as e:
        print(f"TONE ERROR: {e}")
        return {
            "score":            1,
            "pitch_variation":  0.0,
            "energy_variation": 0.0,
            "note":             "Could not evaluate tone",
            "tone_level":       "Moderate",
            "strengths":        [],
            "issues":           [],
            "diagnostics":      {},
        }
    finally:
        for p in [raw_path, clean_path]:
            if p and os.path.exists(p):
                os.remove(p)