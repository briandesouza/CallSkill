"""Audio clip container and macOS playback helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .errors import AudioPlaybackError

FORMAT_SUFFIXES = {
    "mp3": ".mp3",
    "wav": ".wav",
    "pcm": ".pcm",
}


@dataclass(frozen=True)
class AudioClip:
    """Audio bytes plus minimal metadata required for playback."""

    audio_bytes: bytes
    format: str
    content_type: str

    @property
    def suffix(self) -> str:
        return FORMAT_SUFFIXES.get(self.format.lower(), f".{self.format.lower()}")


def play_audio_clip(clip: AudioClip) -> None:
    """Play an audio clip locally.

    V0 playback is intentionally optimized for macOS simplicity and shells out
    to the built-in `afplay` command.
    """
    if not clip.audio_bytes:
        raise AudioPlaybackError("Cannot play an empty audio clip.")

    if sys.platform != "darwin":
        raise AudioPlaybackError("V0 playback only supports macOS.")

    afplay_path = shutil.which("afplay")
    if afplay_path is None:
        raise AudioPlaybackError("The `afplay` command is not available.")

    temp_path = _write_temp_audio_file(clip)
    try:
        result = subprocess.run(
            [afplay_path, str(temp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "afplay exited with a non-zero status."
        raise AudioPlaybackError(stderr)


def _write_temp_audio_file(clip: AudioClip) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=clip.suffix) as temp_file:
        temp_file.write(clip.audio_bytes)
        return Path(temp_file.name)
