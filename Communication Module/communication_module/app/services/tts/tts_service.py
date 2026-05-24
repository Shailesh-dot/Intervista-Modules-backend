"""
tts_service.py
──────────────
Azure Cognitive Services TTS — synthesises clip reference text to WAV bytes.
Called once per session when clips are served (not on every candidate response).
"""

import azure.cognitiveservices.speech as speechsdk
import os
from dotenv import load_dotenv

load_dotenv()

SPEECH_KEY    = os.getenv("AZURE_SPEECH_KEY", "")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
DEFAULT_VOICE = os.getenv("AZURE_SPEECH_VOICE", "en-IN-NeerjaNeural")
# en-IN-NeerjaNeural  — Indian English female
# en-IN-PrabhatNeural — Indian English male
# en-US-JennyNeural   — US English female (use if Indian English not available)


def synthesize_text(text: str, voice: str = None) -> bytes:
    """
    Convert text to speech. Returns raw WAV bytes.
    Raises Exception if synthesis fails — caller should catch this.
    """
    if not SPEECH_KEY:
        raise ValueError("AZURE_SPEECH_KEY not set in .env")

    # Use voice, or AZURE_SPEECH_VOICE, or DEFAULT_VOICE from env, or a fallback
    env_voice = os.getenv("AZURE_SPEECH_VOICE") or os.getenv("DEFAULT_VOICE")
    selected_voice = voice or env_voice or "en-IN-NeerjaNeural"

    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    cfg.speech_synthesis_voice_name = selected_voice
    
    # Explicitly set the output format to WAV (Riff) to match the frontend data URI
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)

    synth  = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    result = synth.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data

    details = result.cancellation_details
    raise Exception(f"TTS failed: {details.reason} — {details.error_details}")