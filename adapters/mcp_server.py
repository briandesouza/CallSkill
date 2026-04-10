"""Portable MCP transport for call mode."""

import asyncio
import contextlib
import threading
import time
from dataclasses import dataclass
from typing import Literal

import sounddevice as sd
from mcp.server.fastmcp import Context, FastMCP

from call_core import (
    AudioPlaybackError,
    ElevenLabsSTTProvider,
    ElevenLabsTTSProvider,
    Recorder,
    STTError,
    SpeechConfigurationError,
    TTSError,
    play_audio_clip,
)

SILENCE_THRESHOLD_SEC = 2.0
MAX_WAIT_SEC = 30.0
HEARTBEAT_INTERVAL_SEC = 5.0

ERROR_MIC_PERMISSION_DENIED = "mic_permission_denied"
ERROR_MIC_UNAVAILABLE = "mic_unavailable"
ERROR_STT_FAILED = "stt_failed"
ERROR_TTS_FAILED = "tts_failed"
ERROR_PLAYBACK_FAILED = "playback_failed"

ListenStatus = Literal["ok", "silence", "error"]
OperationStatus = Literal["ok", "error"]


@dataclass(frozen=True)
class ListenResult:
    """Structured `call_listen()` result."""

    status: ListenStatus
    text: str
    error: str | None


@dataclass(frozen=True)
class OperationResult:
    """Structured `call_speak()` and `call_end()` result."""

    status: OperationStatus
    error: str | None


class _ListenProgressState:
    """Tracks the current listen phase for MCP progress notifications."""

    def __init__(self, *, max_wait_sec: float, silence_threshold_sec: float):
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._max_wait_sec = max_wait_sec
        self._silence_threshold_sec = silence_threshold_sec
        self._phase = "idle"
        self._recording_sec = 0.0
        self._silence_sec = 0.0

    def on_event(self, event: str, data: dict) -> None:
        with self._lock:
            if event == "idle":
                self._phase = "idle"
                self._recording_sec = 0.0
                self._silence_sec = 0.0
            elif event == "recording":
                self._phase = "recording"
                self._recording_sec = 0.0
                self._silence_sec = 0.0
            elif event == "progress":
                self._phase = "recording"
                self._recording_sec = float(data.get("recording_sec", self._recording_sec))
                self._silence_sec = float(data.get("silence_sec", self._silence_sec))
            elif event == "done":
                self._phase = "recorded"
            elif event == "timeout":
                self._phase = "timeout"

    def set_phase(self, phase: str) -> None:
        with self._lock:
            self._phase = phase

    def progress_payload(self) -> tuple[float, float | None, str]:
        with self._lock:
            phase = self._phase
            recording_sec = self._recording_sec
            silence_sec = self._silence_sec

        elapsed_sec = time.monotonic() - self._started_at

        if phase == "idle":
            progress = min(elapsed_sec, self._max_wait_sec)
            message = (
                f"Waiting for speech ({progress:.0f}s/{self._max_wait_sec:.0f}s)"
            )
            return progress, self._max_wait_sec, message

        if phase == "recording":
            progress = max(recording_sec, 0.0)
            if silence_sec > 0:
                message = (
                    f"Recording ({progress:.0f}s, quiet for {silence_sec:.1f}s/"
                    f"{self._silence_threshold_sec:.1f}s)"
                )
            else:
                message = f"Recording ({progress:.0f}s)"
            return progress, None, message

        if phase == "transcribing":
            message = "Transcribing speech..."
            return max(recording_sec, 0.0), None, message

        if phase == "timeout":
            message = "No speech detected before timeout."
            return self._max_wait_sec, self._max_wait_sec, message

        message = "Finalizing recording..."
        return max(recording_sec, 0.0), None, message


mcp = FastMCP(
    "call",
    instructions="Portable call mode tools for listening, speaking, and ending a call.",
    json_response=True,
)


@mcp.tool()
async def call_listen(ctx: Context) -> ListenResult:
    """Listen for speech, transcribe it, and return structured call-mode output."""
    progress_state = _ListenProgressState(
        max_wait_sec=MAX_WAIT_SEC,
        silence_threshold_sec=SILENCE_THRESHOLD_SEC,
    )
    recorder = Recorder(
        silence_threshold_sec=SILENCE_THRESHOLD_SEC,
        max_wait_sec=MAX_WAIT_SEC,
        on_event=progress_state.on_event,
    )

    heartbeat_done = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _emit_progress_heartbeats(ctx, progress_state, heartbeat_done)
    )

    try:
        pcm_data = await asyncio.to_thread(recorder.record)
    except sd.PortAudioError as exc:
        await ctx.error(f"Microphone error: {exc}")
        return ListenResult(status="error", text="", error=_map_mic_error(exc))
    except Exception as exc:  # pragma: no cover - defensive normalization
        await ctx.error(f"Unexpected listen failure: {exc}")
        return ListenResult(status="error", text="", error=ERROR_MIC_UNAVAILABLE)
    finally:
        heartbeat_done.set()
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task

    if pcm_data is None:
        return ListenResult(status="silence", text="", error=None)

    progress_state.set_phase("transcribing")

    try:
        transcript = await asyncio.to_thread(ElevenLabsSTTProvider().transcribe, pcm_data)
    except (SpeechConfigurationError, STTError, ValueError) as exc:
        await ctx.error(f"Speech-to-text failed: {exc}")
        return ListenResult(status="error", text="", error=ERROR_STT_FAILED)

    return ListenResult(status="ok", text=transcript, error=None)


@mcp.tool()
async def call_speak(text: str, ctx: Context) -> OperationResult:
    """Synthesize speech, play it locally, and block until playback completes."""
    try:
        clip = await asyncio.to_thread(ElevenLabsTTSProvider().synthesize, text)
    except (SpeechConfigurationError, TTSError, ValueError) as exc:
        await ctx.error(f"Text-to-speech failed: {exc}")
        return OperationResult(status="error", error=ERROR_TTS_FAILED)

    try:
        await asyncio.to_thread(play_audio_clip, clip)
    except AudioPlaybackError as exc:
        await ctx.error(f"Audio playback failed: {exc}")
        return OperationResult(status="error", error=ERROR_PLAYBACK_FAILED)

    return OperationResult(status="ok", error=None)


@mcp.tool()
async def call_end() -> OperationResult:
    """End call mode and release any long-lived resources.

    V0 does not keep persistent audio resources open between tool calls, so this
    is currently a no-op confirmation for host adapters.
    """
    return OperationResult(status="ok", error=None)


async def _emit_progress_heartbeats(
    ctx: Context,
    progress_state: _ListenProgressState,
    done: asyncio.Event,
) -> None:
    await _report_progress(ctx, progress_state)

    while not done.is_set():
        try:
            await asyncio.wait_for(done.wait(), timeout=HEARTBEAT_INTERVAL_SEC)
        except asyncio.TimeoutError:
            await _report_progress(ctx, progress_state)


async def _report_progress(ctx: Context, progress_state: _ListenProgressState) -> None:
    progress, total, message = progress_state.progress_payload()
    await ctx.report_progress(progress=progress, total=total, message=message)


def _map_mic_error(exc: BaseException) -> str:
    message = str(exc).lower()
    permission_hints = (
        "permission",
        "not permitted",
        "not authorized",
        "authorization",
        "denied",
    )
    if any(hint in message for hint in permission_hints):
        return ERROR_MIC_PERMISSION_DENIED
    return ERROR_MIC_UNAVAILABLE


def main() -> None:
    """Run the portable MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
