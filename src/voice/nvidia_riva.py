"""
NVIDIA Riva speech provider — routes SyllabOS's speech-to-text and
text-to-speech through NVIDIA's hosted Riva NIM endpoints, using the same
free NIM API key (NIM_API_KEY) that already drives syllabus parsing and
schedule building.

Unlike the chat/LLM NIM calls in nim_client.py (a plain REST POST), NVIDIA's
hosted speech models are gRPC services reached at grpc.nvcf.nvidia.com,
addressed by a per-model "function-id" — confirmed against NVIDIA's current
Riva NIM and voice-agent-examples documentation as of September 2026.

Setup (see README "Live voice setup"):
  1. pip3 install -r requirements-voice.txt
  2. Visit https://build.nvidia.com/explore/speech
  3. Open an ASR model (e.g. parakeet-tdt-0.6b-v2) -> "Try API" -> "Python"
     and copy that model's function-id
  4. Do the same for a TTS model (e.g. magpie-tts-multilingual)
  5. Put both function-ids in .env as NVIDIA_ASR_FUNCTION_ID / NVIDIA_TTS_FUNCTION_ID

NVIDIA's hosted speech catalog changes over time — this project has already
hit one retired NIM model (see git history). Function-ids are therefore
never hardcoded here; a missing or invalid one raises VoiceConfigError with
the exact steps above instead of silently failing or guessing a replacement.
"""

import io
import wave
from typing import Optional

from .base import SpeechToText, TextToSpeech
from .errors import MicrophoneError, SpeechEndpointError, VoiceConfigError, VoiceDependencyError

GRPC_ENDPOINT = "grpc.nvcf.nvidia.com:443"
SAMPLE_RATE = 16000  # required input rate for the hosted ASR models


def _import_riva():
    try:
        import riva.client
        return riva.client
    except ImportError as e:
        raise VoiceDependencyError(
            "NVIDIA speech needs the Riva client library.\n"
            "Fix: pip3 install -r requirements-voice.txt"
        ) from e


def _import_audio():
    try:
        import sounddevice as sd
        import numpy as np
        return sd, np
    except ImportError as e:
        raise VoiceDependencyError(
            "Microphone recording and audio playback need sounddevice and numpy.\n"
            "Fix: pip3 install -r requirements-voice.txt"
        ) from e


def _auth(riva_client, api_key: str, function_id: str, what: str):
    if not api_key:
        raise VoiceConfigError(
            f"NIM_API_KEY is not set — NVIDIA {what} needs the same free key as the "
            "rest of SyllabOS.\nFix: get one at https://build.nvidia.com and add it to .env"
        )
    if not function_id:
        raise VoiceConfigError(
            f"Missing NVIDIA {what} function-id.\n"
            "Fix: visit https://build.nvidia.com/explore/speech, open a model, click "
            "'Try API' -> Python, and copy its function-id into .env "
            "(NVIDIA_ASR_FUNCTION_ID / NVIDIA_TTS_FUNCTION_ID)."
        )
    return riva_client.Auth(
        uri=GRPC_ENDPOINT,
        use_ssl=True,
        metadata_args=[
            ["function-id", function_id],
            ["authorization", f"Bearer {api_key}"],
        ],
    )


class NvidiaRivaTTS(TextToSpeech):
    def __init__(self, api_key: str, function_id: str, voice: str, language: str,
                 sample_rate: int = 44100):
        self._riva = _import_riva()
        auth = _auth(self._riva, api_key, function_id, "text-to-speech")
        self._voice = voice
        self._language = language
        self._sample_rate = sample_rate
        try:
            self._service = self._riva.SpeechSynthesisService(auth)
        except Exception as e:
            raise SpeechEndpointError(f"Could not reach the NVIDIA TTS endpoint: {e}") from e

    def speak(self, text: str) -> None:
        sd, np = _import_audio()
        try:
            resp = self._service.synthesize(
                text,
                voice_name=self._voice,
                language_code=self._language,
                sample_rate_hz=self._sample_rate,
            )
        except Exception as e:
            raise SpeechEndpointError(
                f"NVIDIA TTS request failed: {e}\n"
                "Check NVIDIA_TTS_FUNCTION_ID and NVIDIA_TTS_VOICE in .env, and your "
                "internet connection."
            ) from e

        audio = np.frombuffer(resp.audio, dtype=np.int16)
        try:
            sd.play(audio, self._sample_rate)
            sd.wait()
        except Exception as e:
            raise MicrophoneError(f"Could not play audio through your speakers: {e}") from e


class NvidiaRivaSTT(SpeechToText):
    def __init__(self, api_key: str, function_id: str, language: str = "en-US"):
        self._riva = _import_riva()
        auth = _auth(self._riva, api_key, function_id, "speech recognition")
        self._language = language
        try:
            self._service = self._riva.ASRService(auth)
        except Exception as e:
            raise SpeechEndpointError(f"Could not reach the NVIDIA ASR endpoint: {e}") from e

    def listen_once(self, seconds: float = 4.0) -> Optional[str]:
        sd, np = _import_audio()

        try:
            devices = sd.query_devices()
            if not any(d.get("max_input_channels", 0) > 0 for d in devices):
                raise MicrophoneError(
                    "No microphone found.\n"
                    "Fix: connect a microphone, or use the keyboard fallback (press ENTER) instead."
                )
        except MicrophoneError:
            raise
        except Exception as e:
            raise MicrophoneError(f"Could not query audio devices: {e}") from e

        try:
            recording = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                                channels=1, dtype="int16")
            sd.wait()
        except Exception as e:
            raise MicrophoneError(
                f"Could not record from the microphone: {e}\n"
                "Fix: check microphone permissions for your terminal app, or use the "
                "keyboard fallback (press ENTER)."
            ) from e

        wav_bytes = _to_wav_bytes(recording, SAMPLE_RATE)

        config = self._riva.RecognitionConfig(
            encoding=self._riva.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=self._language,
            max_alternatives=1,
            enable_automatic_punctuation=True,
        )
        try:
            response = self._service.offline_recognize(wav_bytes, config)
        except Exception as e:
            raise SpeechEndpointError(
                f"NVIDIA ASR request failed: {e}\n"
                "Check NVIDIA_ASR_FUNCTION_ID in .env, and your internet connection."
            ) from e

        if not response.results:
            return None
        return response.results[0].alternatives[0].transcript


def _to_wav_bytes(recording, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())
    return buf.getvalue()
