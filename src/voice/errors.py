"""
Error types for the voice package. Every one of these is meant to be caught
and shown to the student with the message intact — the message itself is the
fix, not just a diagnosis.
"""


class VoiceError(Exception):
    """Base class for every speech-related failure."""


class VoiceDependencyError(VoiceError):
    """An optional package (riva client, sounddevice, pyttsx3, ...) is missing."""


class VoiceConfigError(VoiceError):
    """Missing or invalid configuration (API key, function-id, voice name)."""


class MicrophoneError(VoiceError):
    """No microphone, permission denied, or audio playback device failure."""


class SpeechEndpointError(VoiceError):
    """The speech endpoint itself rejected the request or was unreachable."""
