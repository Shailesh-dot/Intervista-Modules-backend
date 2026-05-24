import librosa
import numpy as np
import tempfile
import os
import re

FILLER_WORDS = {
    "um", "umm", "uh", "uhh", "uhhh", "hmm", "er", "ah",
    "like", "you know", "so",
    "basically", "actually", "only", "itself",
    "na", "no", "right",
}


def _count_fillers(transcript: str) -> dict:
    lower = transcript.lower()
    total = 0
    words_used = []
    
    for filler in FILLER_WORDS:
        count = len(re.findall(r'\b' + re.escape(filler) + r'\b', lower))
        if count > 0:
            total += count
            words_used.append(f"{filler}({count})")
            
    return {"total": total, "words_used": words_used}


def _analyze_pauses(timestamps: list) -> dict:
    if not timestamps or len(timestamps) < 2:
        return {"count": 0, "avg_duration": 0.0}
    pauses = []
    for i in range(1, len(timestamps)):
        gap = timestamps[i].get("start", 0) - timestamps[i - 1].get("end", 0)
        if gap > 0.5:
            pauses.append(round(gap, 2))
    return {
        "count":        len(pauses),
        "avg_duration": round(np.mean(pauses), 2) if pauses else 0.0,
    }


def _get_duration(timestamps: list, audio_file) -> float:
    if timestamps:
        last = timestamps[-1]
        dur  = last.get("end", 0) or last.get("start", 1)
        if dur > 0:
            return dur
    if audio_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_file.file.read())
            tmp = f.name
        try:
            y, sr = librosa.load(tmp, sr=None)
            return librosa.get_duration(y=y, sr=sr)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    return 1.0


def analyze_fluency(transcript: str, timestamps: list, audio_file=None) -> dict:
    try:
        words       = [w for w in transcript.split() if w.strip()]
        total_words = len(words)
        duration    = _get_duration(timestamps, audio_file)

        wpm          = round((total_words / max(duration, 1)) * 60, 1)
        filler_results = _count_fillers(transcript)
        filler_count = filler_results["total"]
        filler_words = filler_results["words_used"]
        filler_rate  = round((filler_count / max(total_words, 1)) * 100, 1)
        pause_data   = _analyze_pauses(timestamps)

        # WPM score
        if wpm < 90 or wpm > 180:
            wpm_score = 0
        elif wpm < 110 or wpm > 165:
            wpm_score = 1
        else:
            wpm_score = 2

        # Deductions
        filler_deduction = 2 if filler_rate > 10 else (1 if filler_rate > 5 else 0)
        long_pauses      = sum(1 for _ in range(pause_data["count"])
                               if pause_data["avg_duration"] > 2.0)
        pause_deduction  = 1 if long_pauses > 1 else 0

        score = max(0, min(2, wpm_score - filler_deduction - pause_deduction))

        if score == 2:
            note = "Smooth and natural speaking pace"
        elif score == 1:
            if filler_rate > 5:
                note = "Good pace but too many filler words"
            else:
                note = "Slightly slow or fast — pace needs adjustment"
        else:
            note = "Fluency needs significant improvement"

        return {
            "score":       score,
            "wpm":         wpm,
            "filler_rate": filler_rate,
            "filler_words": filler_words,
            "pauses":      pause_data,
            "note":        note,
        }

    except Exception as e:
        print(f"FLUENCY ERROR: {e}")
        return {"score": 1, "wpm": 0.0, "filler_rate": 0.0,
                "pauses": {"count": 0, "avg_duration": 0.0},
                "note": "Could not evaluate fluency"}