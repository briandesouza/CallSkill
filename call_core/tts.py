"""ElevenLabs text-to-speech provider."""

from __future__ import annotations

import os
import sys
from typing import Protocol, Tuple

import requests

from .audio import AudioClip, play_audio_clip
from .errors import SpeechConfigurationError, TTSError

ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_TTS_VOICE_ID = "tMvyQtpCVQ0DkixuYm6J"
DEFAULT_TTS_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_TTS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_TTS_TIMEOUT: Tuple[float, float] = (10.0, 60.0)


class TTSProvider(Protocol):
    """Text-to-speech provider contract."""

    def synthesize(self, text: str) -> AudioClip:
        """Synthesize spoken audio from text."""


class ElevenLabsTTSProvider:
    """Synthesize speech with ElevenLabs using macOS-friendly MP3 output."""

    def __init__(
        self,
        api_key: str = None,
        voice_id: str = None,
        model_id: str = None,
        output_format: str = DEFAULT_TTS_OUTPUT_FORMAT,
        timeout: Tuple[float, float] = DEFAULT_TTS_TIMEOUT,
        session: requests.Session = None,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise SpeechConfigurationError(
                "ELEVENLABS_API_KEY is not set. "
                "Export it in your shell (export ELEVENLABS_API_KEY=your-key) "
                "and restart Claude Code."
            )

        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_TTS_VOICE_ID)
        self.model_id = model_id or os.getenv(
            "ELEVENLABS_TTS_MODEL_ID", DEFAULT_TTS_MODEL_ID
        )
        self.output_format = output_format
        self.timeout = timeout
        self.session = session or requests.Session()

    def synthesize(self, text: str) -> AudioClip:
        """Generate a speech clip for the provided text."""
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("text must not be empty.")

        try:
            response = self.session.post(
                f"{ELEVENLABS_API_BASE_URL}/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                params={"output_format": self.output_format},
                json={
                    "text": normalized_text,
                    "model_id": self.model_id,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TTSError("Failed to reach ElevenLabs text-to-speech.") from exc

        if not response.ok:
            raise TTSError(_error_message("ElevenLabs text-to-speech failed", response))

        return AudioClip(
            audio_bytes=response.content,
            format=_audio_format_from_output_format(self.output_format),
            content_type=response.headers.get("Content-Type", "audio/mpeg"),
        )


def _audio_format_from_output_format(output_format: str) -> str:
    return output_format.split("_", 1)[0].lower()


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
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print("Usage: python -m call_core.tts \"hello from call mode\"")
        raise SystemExit(2)

    clip = ElevenLabsTTSProvider().synthesize(text)
    play_audio_clip(clip)
