"""
Wake-phrase matching for "Good morning, Sunshine", plus the keyboard
fallback listener used when no microphone/ASR is available, or the room is
too noisy for reliable speech recognition.
"""

import re
import threading
from difflib import SequenceMatcher
from typing import Callable

TRIGGER_PHRASE = "good morning sunshine"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z ]", " ", text.lower()).strip()
    # note: non-letters become spaces (not dropped) so "sunshine!" and
    # "sunshine," don't get glued to neighboring words.


def matches_trigger(text: str, threshold: float = 0.72) -> bool:
    """
    True if `text` is a plausible utterance of "Good morning, Sunshine",
    tolerant of ASR casing/punctuation noise and small transcription errors.
    """
    if not text:
        return False

    normalized = re.sub(r"\s+", " ", _normalize(text)).strip()
    if not normalized:
        return False

    if TRIGGER_PHRASE in normalized:
        return True

    if "good morning" in normalized and "sunshine" in normalized:
        return True

    ratio = SequenceMatcher(None, normalized, TRIGGER_PHRASE).ratio()
    return ratio >= threshold


class KeyboardFallback:
    """
    Background thread that fires `on_trigger` whenever the student presses
    ENTER at the terminal — the noisy-room / broken-microphone fallback
    required alongside the spoken trigger.
    """

    def __init__(self, on_trigger: Callable[[], None]):
        self._on_trigger = on_trigger
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                input()
            except (EOFError, RuntimeError):
                return
            if not self._stop.is_set():
                self._on_trigger()
