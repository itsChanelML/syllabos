import unittest

from . import _pathfix  # noqa: F401

from voice import get_stt, get_tts
from voice.errors import (
    MicrophoneError,
    SpeechEndpointError,
    VoiceConfigError,
    VoiceDependencyError,
    VoiceError,
)


class TestErrorHierarchy(unittest.TestCase):
    def test_all_specific_errors_are_voice_errors(self):
        for cls in (VoiceDependencyError, VoiceConfigError, MicrophoneError, SpeechEndpointError):
            self.assertTrue(issubclass(cls, VoiceError))


class TestGetTts(unittest.TestCase):
    def test_never_raises_even_with_no_config_at_all(self):
        # No NIM key, no function-id, possibly no riva/pyttsx3 installed —
        # this must degrade gracefully, never crash the CLI.
        try:
            tts, warning = get_tts("nvidia", api_key="")
        except VoiceError:
            self.fail("get_tts() must never raise — it should return (None, warning) instead")

        if tts is None:
            self.assertIsNotNone(warning)
        # if a provider *was* returned, it fell back to the offline one because
        # NVIDIA had no api key/function-id configured
        if warning:
            self.assertIn("NVIDIA", warning)

    def test_system_provider_requested_directly_does_not_mention_nvidia_fallback(self):
        try:
            tts, warning = get_tts("system", api_key="")
        except VoiceError:
            self.fail("get_tts() must never raise")
        # requesting "system" directly should never produce an "NVIDIA unavailable" warning
        if warning:
            self.assertNotIn("NVIDIA", warning)


class TestGetStt(unittest.TestCase):
    def test_system_provider_has_no_speech_recognition(self):
        stt, warning = get_stt("system", api_key="somekey")
        self.assertIsNone(stt)
        self.assertIsNotNone(warning)
        self.assertIn("keyboard", warning.lower())

    def test_nvidia_without_config_falls_back_to_keyboard_with_clear_warning(self):
        stt, warning = get_stt("nvidia", api_key="")
        self.assertIsNone(stt)
        self.assertIsNotNone(warning)
        self.assertIn("NVIDIA", warning)


if __name__ == "__main__":
    unittest.main()
