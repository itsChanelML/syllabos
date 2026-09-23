"""
Offline fallback voice provider. No API key, no network, no NVIDIA account —
uses the operating system's built-in text-to-speech engine via pyttsx3.

This is the provider SyllabOS falls back to (with a visible warning, never
silently) whenever NVIDIA speech isn't configured or isn't reachable, and the
provider used for a fully offline workshop demo.

There is no offline speech-to-text counterpart here on purpose — reliably
recognizing "Good morning, Sunshine" without a cloud model is out of scope
for this project. Use the keyboard fallback instead (see trigger.py).
"""

from .base import TextToSpeech
from .errors import VoiceDependencyError


class SystemTTS(TextToSpeech):
    def __init__(self):
        try:
            import pyttsx3
        except ImportError as e:
            raise VoiceDependencyError(
                "Offline text-to-speech needs pyttsx3.\n"
                "Fix: pip3 install -r requirements-voice.txt"
            ) from e
        self._engine = pyttsx3.init()

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()
