"""
Orchestrates `--listen`: repeatedly records short audio clips (if NVIDIA
speech recognition is available) and/or waits for the ENTER-key fallback,
firing the morning briefing the first time either one recognizes
"Good morning, Sunshine". Runs only while the script is running — there is
no background daemon or persistence.
"""

import threading
import time
from typing import Callable, Optional

from display import log_a, log_t, log_gr
from trigger import KeyboardFallback, matches_trigger
from voice.errors import VoiceError


def run_listen_loop(stt, on_trigger: Callable[[], None], once: bool = False,
                     clip_seconds: float = 4.0):
    trigger_event = threading.Event()
    lock = threading.Lock()
    fired_once = {"value": False}

    def fire():
        with lock:
            if once and fired_once["value"]:
                return
            fired_once["value"] = True
        trigger_event.set()

    keyboard = KeyboardFallback(on_trigger=fire)
    keyboard.start()

    log_t('Listening for "Good morning, Sunshine"...')
    log_gr("  Press ENTER at any time to trigger the briefing manually.")
    log_gr("  Ctrl+C to stop listening.\n")

    mic_warned = False

    try:
        while True:
            if trigger_event.is_set():
                trigger_event.clear()
                on_trigger()
                if once:
                    break
                log_t('\nListening again for "Good morning, Sunshine"...')
                continue

            if stt is None:
                time.sleep(0.2)
                continue

            try:
                transcript = stt.listen_once(seconds=clip_seconds)
            except VoiceError as e:
                if not mic_warned:
                    log_a(f"Microphone/speech recognition unavailable:\n{e}")
                    log_a("Continuing with the keyboard fallback only (press ENTER).")
                    mic_warned = True
                time.sleep(1)
                continue

            if transcript:
                log_gr(f'  heard: "{transcript}"')
                if matches_trigger(transcript):
                    fire()
    except KeyboardInterrupt:
        log_gr("\nStopped listening.")
    finally:
        keyboard.stop()
