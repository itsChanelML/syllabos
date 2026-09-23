"""
Voice provider factory. Selects NVIDIA Riva or the offline system fallback
based on the requested provider, and always degrades — visibly, never
silently — instead of crashing a live demo:

  - get_tts(): tries NVIDIA (if requested), falls back to the offline system
    voice on any VoiceError, and only returns (None, warning) if neither
    works. The caller then knows to print text instead of speaking it.
  - get_stt(): NVIDIA only (the offline provider has no speech recognition).
    Returns (None, warning) if unavailable — the caller falls back to the
    keyboard trigger.
"""

import os
from typing import Optional, Tuple

from .base import SpeechToText, TextToSpeech
from .errors import VoiceError
from .system_voice import SystemTTS

__all__ = ["get_tts", "get_stt", "TextToSpeech", "SpeechToText", "VoiceError"]


def get_tts(provider: str, api_key: str) -> Tuple[Optional[TextToSpeech], Optional[str]]:
    warnings = []

    if provider == "nvidia":
        try:
            from .nvidia_riva import NvidiaRivaTTS
            return NvidiaRivaTTS(
                api_key=api_key,
                function_id=os.environ.get("NVIDIA_TTS_FUNCTION_ID", ""),
                voice=os.environ.get("NVIDIA_TTS_VOICE", "Magpie-Multilingual.EN-US.Female-1"),
                language=os.environ.get("NVIDIA_TTS_LANGUAGE", "en-US"),
                sample_rate=int(os.environ.get("NVIDIA_TTS_SAMPLE_RATE", "44100")),
            ), None
        except VoiceError as e:
            warnings.append(f"NVIDIA text-to-speech unavailable, trying the offline voice instead.\n{e}")

    try:
        return SystemTTS(), ("\n\n".join(warnings) or None)
    except VoiceError as e:
        warnings.append(str(e))
        return None, "\n\n".join(warnings)


def get_stt(provider: str, api_key: str) -> Tuple[Optional[SpeechToText], Optional[str]]:
    if provider == "nvidia":
        try:
            from .nvidia_riva import NvidiaRivaSTT
            return NvidiaRivaSTT(
                api_key=api_key,
                function_id=os.environ.get("NVIDIA_ASR_FUNCTION_ID", ""),
                language=os.environ.get("NVIDIA_ASR_LANGUAGE", "en-US"),
            ), None
        except VoiceError as e:
            return None, f"NVIDIA speech recognition unavailable — keyboard fallback only.\n{e}"

    return None, "System voice provider has no speech recognition — keyboard fallback only (press ENTER)."
