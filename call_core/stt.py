"""ElevenLabs speech-to-text provider."""

from __future__ import annotations

import os
from typing import Protocol, Tuple

import requests

from .errors import SpeechConfigurationError, STTError

ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_STT_MODEL_ID = "scribe_v2"
DEFAULT_STT_TIMEOUT: Tuple[float, float] = (10.0, 60.0)
PCM_UPLOAD_FORMAT = "pcm_s16le_16"


class STTProvider(Protocol):
    """Speech-to-text provider contract."""

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe mono 16kHz 16-bit PCM audio into text."""


class ElevenLabsSTTProvider:
    """Transcribe recorded PCM audio with ElevenLabs Scribe."""

    def __init__(
        self,
        api_key: str = None,
        model_id: str = DEFAULT_STT_MODEL_ID,
        timeout: Tuple[float, float] = DEFAULT_STT_TIMEOUT,
        session: requests.Session = None,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise SpeechConfigurationError(
                "ELEVENLABS_API_KEY is not set. "
                "Export it in your shell (export ELEVENLABS_API_KEY=your-key) "
                "and restart Claude Code."
            )

        self.model_id = model_id
        self.timeout = timeout
        self.session = session or requests.Session()

    def transcribe(self, audio_bytes: bytes) -> str:
        """Send raw PCM audio to ElevenLabs and return transcript text."""
        if not audio_bytes:
            raise ValueError("audio_bytes must not be empty.")

        try:
            response = self.session.post(
                f"{ELEVENLABS_API_BASE_URL}/speech-to-text",
                headers={"xi-api-key": self.api_key},
                data={
                    "model_id": self.model_id,
                    "file_format": PCM_UPLOAD_FORMAT,
                    "tag_audio_events": "false",
                    "timestamps_granularity": "none",
                },
                files={
                    "file": (
                        "audio.pcm",
                        audio_bytes,
                        "application/octet-stream",
                    )
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise STTError("Failed to reach ElevenLabs speech-to-text.") from exc

        if not response.ok:
            raise STTError(_error_message("ElevenLabs speech-to-text failed", response))

        try:
            payload = response.json()
        except ValueError as exc:
            raise STTError("ElevenLabs speech-to-text returned invalid JSON.") from exc

        text = payload.get("text")
        if text is None:
            raise STTError("ElevenLabs speech-to-text response was missing `text`.")

        return text.strip()


def _error_message(prefix: str, response: requests.Response) -> str:
    detail = ""
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail_value = payload.get("detail") or payload.get("message")
        if detail_value:
            detail = str(detail_value)

    if detail:
        return f"{prefix}: {response.status_code} {detail}"
    return f"{prefix}: HTTP {response.status_code}."


if __name__ == "__main__":
    from .recorder import Recorder

    recorder = Recorder()
    pcm_data = recorder.record()

    if pcm_data is None:
        print("No speech detected.")
        raise SystemExit(0)

    transcript = ElevenLabsSTTProvider().transcribe(pcm_data)
    print(transcript)
