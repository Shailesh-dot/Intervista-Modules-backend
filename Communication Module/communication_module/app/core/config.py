import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Azure Speech (TTS for listening assessment) ───────────────────────────────
SPEECH_KEY    = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "centralindia")

# Default Azure neural voice — Indian English female
# Full list: https://learn.microsoft.com/azure/cognitive-services/speech-service/language-support
DEFAULT_VOICE = os.getenv("AZURE_VOICE", "en-IN-ArjunNeural")