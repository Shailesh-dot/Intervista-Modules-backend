from groq import Groq
import tempfile
import os
from dotenv import load_dotenv
import math

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def transcribe_audio(audio_file) -> dict:
    temp_file_path = None

    try:
        audio_file.file.seek(0)
        data = audio_file.file.read()

        if not data:
            raise Exception("Empty audio file")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            temp.write(data)
            temp_file_path = temp.name

        with open(temp_file_path, "rb") as f:
            response = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3",
                response_format="verbose_json",
                temperature=0.2,
                language="en",   # small randomness improves coverage
            )

        response_dict = response.model_dump()
        
        print("Whisper response:", response_dict)

        text = response_dict.get("text", "").strip()
        segments = response_dict.get("segments", [])

        # ✅ FIX 1: Very safe silence detection (NOT aggressive)
        if segments:
            if all(s.get("no_speech_prob", 0) > 0.85 for s in segments):
                return {"text": "", "timestamps": [], "words": []}

        # ✅ FIX 2: Remove ONLY obvious junk (not real speech)
        BAD_PHRASES = [
            "thanks for watching",
            "subscribe",
            "amara.org",
            "subtitles by"
        ]

        text_lower = text.lower()
        if any(p in text_lower for p in BAD_PHRASES):
            return {"text": "", "timestamps": [], "words": []}

        # ✅ FIX 3: Proper word confidence calculation
        words = response_dict.get("words", [])

        if not words and segments:
            for seg in segments:
                logprob = seg.get("avg_logprob", -1.0)

                # Convert logprob → probability correctly
                prob = max(0.0, min(1.0, math.exp(logprob)))

                for w in seg.get("text", "").split():
                    words.append({
                        "word": w.strip(),
                        "probability": round(prob, 3),
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                    })

        return {
            "text": text,
            "timestamps": segments,
            "words": words,
        }

    except Exception as e:
        print("WHISPER ERROR:", e)
        return {"text": "", "timestamps": [], "words": []}

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)