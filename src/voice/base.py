"""
Speech provider interfaces. Any provider (NVIDIA Riva, the offline system
fallback, or a future third-party service) implements these two small
contracts so the rest of SyllabOS never depends on a specific vendor.
"""

from abc import ABC, abstractmethod
from typing import Optional


class TextToSpeech(ABC):
    @abstractmethod
    def speak(self, text: str) -> None:
        """Synthesize and play `text` out loud. Raises VoiceError on failure."""


class SpeechToText(ABC):
    @abstractmethod
    def listen_once(self, seconds: float = 4.0) -> Optional[str]:
        """
        Record `seconds` of audio from the microphone and return the
        transcript, or None if nothing intelligible was captured.
        Raises VoiceError (e.g. MicrophoneError) on failure.
        """
