import unittest

from . import _pathfix  # noqa: F401  (adds src/ to sys.path)

from trigger import matches_trigger


class TestTriggerMatching(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertTrue(matches_trigger("Good morning, Sylvia"))

    def test_case_and_punctuation_insensitive(self):
        self.assertTrue(matches_trigger("good morning sylvia"))
        self.assertTrue(matches_trigger("GOOD MORNING, SYLVIA!"))
        self.assertTrue(matches_trigger("good... morning, sylvia?"))

    def test_extra_words_around_phrase(self):
        self.assertTrue(matches_trigger("well good morning sylvia how are you"))

    def test_minor_asr_noise_still_matches(self):
        # small transcription slip ("sylvias") should still be close enough
        self.assertTrue(matches_trigger("good morning sylvias"))

    def test_empty_or_none_does_not_match(self):
        self.assertFalse(matches_trigger(""))
        self.assertFalse(matches_trigger(None))

    def test_unrelated_speech_does_not_match(self):
        self.assertFalse(matches_trigger("what's the weather like today"))
        self.assertFalse(matches_trigger("hey can you open my calendar"))

    def test_partial_phrase_alone_does_not_match(self):
        # "good morning" without "sylvia" should not fire the briefing
        self.assertFalse(matches_trigger("good morning everyone"))
        self.assertFalse(matches_trigger("sylvia is nice today"))

    def test_old_wake_word_no_longer_matches(self):
        # regression: whole-phrase similarity used to let "Sunshine" (the
        # prior wake word) slip past, since "good morning ___" alone was
        # often enough to clear the threshold regardless of the name
        self.assertFalse(matches_trigger("Good morning, Sunshine"))
        self.assertFalse(matches_trigger("good morning sunshine"))


if __name__ == "__main__":
    unittest.main()
