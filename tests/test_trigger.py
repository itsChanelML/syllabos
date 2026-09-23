import unittest

from . import _pathfix  # noqa: F401  (adds src/ to sys.path)

from trigger import matches_trigger


class TestTriggerMatching(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertTrue(matches_trigger("Good morning, Sunshine"))

    def test_case_and_punctuation_insensitive(self):
        self.assertTrue(matches_trigger("good morning sunshine"))
        self.assertTrue(matches_trigger("GOOD MORNING, SUNSHINE!"))
        self.assertTrue(matches_trigger("good... morning, sunshine?"))

    def test_extra_words_around_phrase(self):
        self.assertTrue(matches_trigger("well good morning sunshine how are you"))

    def test_minor_asr_noise_still_matches(self):
        # small transcription slip ("sunshines") should still be close enough
        self.assertTrue(matches_trigger("good morning sunshines"))

    def test_empty_or_none_does_not_match(self):
        self.assertFalse(matches_trigger(""))
        self.assertFalse(matches_trigger(None))

    def test_unrelated_speech_does_not_match(self):
        self.assertFalse(matches_trigger("what's the weather like today"))
        self.assertFalse(matches_trigger("hey can you open my calendar"))

    def test_partial_phrase_alone_does_not_match(self):
        # "good morning" without "sunshine" should not fire the briefing
        self.assertFalse(matches_trigger("good morning everyone"))
        self.assertFalse(matches_trigger("sunshine is nice today"))


if __name__ == "__main__":
    unittest.main()
