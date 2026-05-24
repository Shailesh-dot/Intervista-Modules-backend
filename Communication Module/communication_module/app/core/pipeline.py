"""
pipeline.py  v2
────────────────
Speaking pipeline — redesigned for minimum LLM calls.

Old: per-question → 1 Whisper + 1 grammar LLM + 1 comprehension LLM
     3 questions × 3 calls = 9 LLM calls

New: per-question → 1 Whisper (unavoidable, sequential per audio file)
     All questions combined → 1 LLM call (grammar + comprehension together)
     3 Whisper + 1 LLM = 4 total calls per session

Audio-only evals (pronunciation, fluency, tone) remain per-question
but are pure CPU — zero network calls.
"""

import asyncio
import io

from app.services.speech.whisper_service import transcribe_audio
from app.services.fluency.fluency_analyzer import analyze_fluency
from app.services.tone.tone_analyzer import analyze_tone
from app.services.pronunciation.pronunciation_service import evaluate_pronunciation
from app.services.grammar.llama_service import evaluate_speaking_session
from app.core.scoring_engine import aggregate_scores


def is_valid_speech(text: str, segments: list, words: list) -> bool:
    if not text or not segments:
        print(f"INVALID SPEECH: Empty text or segments")
        return False
        
    word_count = len(words)
    duration = segments[-1].get("end", 0.0)
    
    avg_no_speech = sum(s.get("no_speech_prob", 0.0) for s in segments) / len(segments)
    avg_logprob = sum(s.get("avg_logprob", 0.0) for s in segments) / len(segments)
    
    if avg_no_speech > 0.5:
        print(f"INVALID SPEECH: Rule 1 Failed | avg_no_speech ({avg_no_speech:.3f}) > 0.5 | Text: '{text}'")
        return False
        
    if word_count < 8:
        print(f"INVALID SPEECH: Rule 2 Failed | word_count ({word_count}) < 8 | Text: '{text}'")
        return False
        
    if avg_logprob < -1.2:
        print(f"INVALID SPEECH: Rule 3 Failed | avg_logprob ({avg_logprob:.3f}) < -1.2 | Text: '{text}'")
        return False
        
    if duration > 0.0 and word_count > duration * 3:
        print(f"INVALID SPEECH: Rule 4 Failed | hallucination density word_count ({word_count}) > duration * 3 ({duration * 3:.1f}) | Text: '{text}'")
        return False
        
    if text.lower().strip() in ["thank you", "thanks", "yes", "okay"]:
        print(f"INVALID SPEECH: Rule 5 Failed | known hallucination | Text: '{text}'")
        return False
        
    print(f"VALID SPEECH: Passed all checks! | Text: '{text}'")
    return True



class BufferedFile:
    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)


# ─────────────────────────────────────────────────────────────────────────────
# Single-question pipeline (used by /evaluate endpoint — one audio at a time)
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(audio_file, question: str) -> dict:
    """
    Evaluate a single audio response.

    LLM calls: 1 Whisper + 1 combined LLM (grammar+comprehension)
    Audio calls: pronunciation, fluency, tone (CPU only)
    Total external calls: 2
    """
    # ── Transcription ─────────────────────────────────────────────────────────
    audio_file.file.seek(0)
    audio_bytes = audio_file.file.read()
    audio_file.file.seek(0)

    transcript_data = await transcribe_audio(audio_file)
    transcript      = transcript_data.get("text", "").strip()
    segments        = transcript_data.get("timestamps", [])
    words           = transcript_data.get("words", [])

    print(f"TRANSCRIPT ({len(transcript)} chars): {transcript[:120]}…")
    print(f"SEGMENTS: {len(segments)} | WORDS: {len(words)}")

    if not is_valid_speech(transcript, segments, words):
        return {
            "status": "no_valid_speech",
            "message": "No valid speech detected. Please provide a complete answer.",
            "scores": {
                "pronunciation": 0,
                "fluency": 0,
                "tone": 0,
                "grammar": 0,
                "comprehension": 0
            }
        }

    def _run_sync_evals():

        local_fluency = BufferedFile(audio_bytes)
        local_tone    = BufferedFile(audio_bytes)

        # ── CPU-only evals (no network) ───────────────────────────────────────
        try:
            pronunciation = evaluate_pronunciation(
                expected_text    = question,
                spoken_text      = transcript,
                whisper_segments = segments,
                whisper_words    = words,
            )
            print(f"PRONUNCIATION: score={pronunciation['score']} composite={pronunciation.get('composite_score')}")
        except Exception as e:
            print(f"PRONUNCIATION ERROR: {e}")
            pronunciation = {"score": 1, "clarity": 0.75, "consistency": 0.75,
                             "composite_score": 0.5, "note": "Could not evaluate pronunciation"}

        try:
            fluency = analyze_fluency(transcript, segments, local_fluency)
            print(f"FLUENCY: score={fluency['score']} wpm={fluency.get('wpm')} fillers={fluency.get('filler_words')}")
        except Exception as e:
            print(f"FLUENCY ERROR: {e}")
            fluency = {"score": 1, "wpm": 0.0, "filler_rate": 0.0,
                       "pauses": {"count": 0, "avg_duration": 0.0}, "note": "Could not evaluate fluency"}

        try:
            tone = analyze_tone(local_tone)
            print(f"TONE: score={tone['score']}")
        except Exception as e:
            print(f"TONE ERROR: {e}")
            tone = {"score": 1, "pitch_variation": 30.0, "energy_variation": 0.3,
                    "note": "Could not evaluate tone"}

        # ── Single combined LLM call (grammar + comprehension) ────────────────
        try:
            llm_results = evaluate_speaking_session([{"question": question, "answer": transcript}])
            grammar       = llm_results[0]["grammar"]
            comprehension = llm_results[0]["comprehension"]
            print(f"GRAMMAR: score={grammar.get('score')} mistakes={len(grammar.get('mistakes', []))}")
            print(f"COMPREHENSION: score={comprehension.get('score')} relevance={comprehension.get('relevance')} completeness={comprehension.get('completeness')}")
        except Exception as e:
            print(f"LLM EVAL ERROR: {e}")
            grammar       = {"score": 1, "mistakes": [], "note": "Could not evaluate grammar"}
            comprehension = {"score": 1, "relevance": 0.5, "completeness": 0.5,
                             "note": "Could not evaluate comprehension"}

        return aggregate_scores(
            pronunciation = pronunciation,
            fluency       = fluency,
            tone          = tone,
            grammar       = grammar,
            comprehension = comprehension,
        )

    final              = await asyncio.to_thread(_run_sync_evals)
    final["transcript"] = transcript
    return final


# ─────────────────────────────────────────────────────────────────────────────
# Session pipeline (used by /speaking/aggregate — all 3 answers at once)
# ─────────────────────────────────────────────────────────────────────────────

async def run_session_pipeline(
    audio_files: list,          # list of (audio_file, question_str) tuples
) -> list[dict]:
    """
    Evaluate all speaking answers in a session.

    Call budget:
      - 1 Whisper call per audio file  (unavoidable — sequential per audio)
      - 1 combined LLM call for all grammar + comprehension (new)
      - CPU-only calls for pronunciation / fluency / tone

    Total external calls: len(audio_files) Whisper + 1 LLM
    """
    # ── Step 1: Transcribe all audio files ───────────────────────────────────
    transcriptions = []
    audio_bytes_list = []
    for audio_file, question in audio_files:
        try:
            audio_file.file.seek(0)
            audio_bytes = audio_file.file.read()
            audio_bytes_list.append(audio_bytes)
            audio_file.file.seek(0)
            td = await transcribe_audio(audio_file)
            transcriptions.append({
                "question": question,
                "text":     td.get("text", "").strip(),
                "segments": td.get("timestamps", []),
                "words":    td.get("words", []),
            })
            print(f"TRANSCRIPT Q{len(transcriptions)}: {td.get('text','')[:80]}…")
        except Exception as e:
            print(f"TRANSCRIPTION ERROR: {e}")
            transcriptions.append({"question": question, "text": "", "segments": [], "words": []})
            audio_bytes_list.append(b"")

    # ── Step 2: Combined LLM call for grammar + comprehension ─────────────────
    qa_pairs = []
    valid_indices = []
    for i, t in enumerate(transcriptions):
        if is_valid_speech(t["text"], t["segments"], t["words"]):
            qa_pairs.append({"question": t["question"], "answer": t["text"]})
            valid_indices.append(i)

    # Initialize with default fallback for all, then overwrite valid ones
    llm_results = [
        {"grammar": {"score": 1, "mistakes": [], "note": "Could not evaluate"},
         "comprehension": {"score": 1, "relevance": 0.5, "completeness": 0.5, "note": "Could not evaluate"}}
        for _ in transcriptions
    ]

    if qa_pairs:
        try:
            actual_llm_results = await asyncio.to_thread(evaluate_speaking_session, qa_pairs)
            for valid_idx, llm_res in zip(valid_indices, actual_llm_results):
                llm_results[valid_idx] = llm_res
        except Exception as e:
            print(f"COMBINED LLM ERROR: {e}")

    # ── Step 3: CPU-only evals per question + aggregate ──────────────────────
    results = []
    for i, (td, audio_bytes) in enumerate(zip(transcriptions, audio_bytes_list)):
        transcript = td["text"]
        segments   = td["segments"]
        words      = td["words"]
        question   = td["question"]

        if not is_valid_speech(transcript, segments, words):
            results.append({
                "status": "no_valid_speech",
                "message": "No valid speech detected. Please provide a complete answer.",
                "scores": {
                    "pronunciation": 0,
                    "fluency": 0,
                    "tone": 0,
                    "grammar": 0,
                    "comprehension": 0
                }
            })
            continue

        local_fluency = BufferedFile(audio_bytes)
        local_tone    = BufferedFile(audio_bytes)

        try:
            pronunciation = evaluate_pronunciation(
                expected_text=question, spoken_text=transcript,
                whisper_segments=segments, whisper_words=words,
            )
            print(f"PRONUNCIATION Q{i+1}: score={pronunciation['score']} composite={pronunciation.get('composite_score')}")
        except Exception as e:
            print(f"PRONUNCIATION ERROR Q{i+1}: {e}")
            pronunciation = {"score": 1, "clarity": 0.75, "consistency": 0.75,
                             "composite_score": 0.5, "note": "Could not evaluate pronunciation"}

        try:
            fluency = analyze_fluency(transcript, segments, local_fluency)
            print(f"FLUENCY Q{i+1}: score={fluency['score']} wpm={fluency.get('wpm')} fillers={fluency.get('filler_words')}")
        except Exception as e:
            print(f"FLUENCY ERROR Q{i+1}: {e}")
            fluency = {"score": 1, "wpm": 0.0, "filler_rate": 0.0,
                       "pauses": {"count": 0, "avg_duration": 0.0}, "note": "Could not evaluate fluency"}

        try:
            tone = analyze_tone(local_tone)
            print(f"TONE Q{i+1}: score={tone['score']}")
        except Exception as e:
            print(f"TONE ERROR Q{i+1}: {e}")
            tone = {"score": 1, "pitch_variation": 30.0, "energy_variation": 0.3,
                    "note": "Could not evaluate tone"}

        grammar       = llm_results[i]["grammar"]
        comprehension = llm_results[i]["comprehension"]
        print(f"GRAMMAR Q{i+1}: score={grammar.get('score')} mistakes={len(grammar.get('mistakes', []))}")
        print(f"COMPREHENSION Q{i+1}: score={comprehension.get('score')} relevance={comprehension.get('relevance')} completeness={comprehension.get('completeness')}")

        result = aggregate_scores(
            pronunciation=pronunciation,
            fluency=fluency,
            tone=tone,
            grammar=grammar,
            comprehension=comprehension,
        )
        result["transcript"] = transcript
        results.append(result)

    return results