---
name: Implementation progress
description: Tracks which implementation phases are complete and what's next for call mode
type: project
---

## Implementation phases

- **Phase 1: Recorder** — COMPLETE
  - `call_core/recorder.py` — mic recording + webrtcvad silence detection
  - `requirements.txt` — sounddevice, webrtcvad
  - VAD aggressiveness set to 3 (needed for noisy environments)
  - Energy floor approach was tried and removed — VAD alone works better
  - Test via: `.venv/bin/python -m call_core.recorder`

- **Phase 2: Core speech providers + playback** — COMPLETE
  - `call_core/stt.py` — ElevenLabs STT
  - `call_core/tts.py` — ElevenLabs TTS
  - `call_core/audio.py` — macOS playback via `afplay`
  - `call_core/errors.py` — shared speech/playback exceptions
  - `call_core/__init__.py` — lazy exports so module entrypoints run cleanly via `python -m`
  - Defaults: `scribe_v2`, voice `tMvyQtpCVQ0DkixuYm6J`, TTS model `eleven_flash_v2_5`
  - Config: `ELEVENLABS_API_KEY` required, `ELEVENLABS_VOICE_ID` and `ELEVENLABS_TTS_MODEL_ID` optional
  - Test via: `.venv/bin/python -m call_core.stt` and `.venv/bin/python -m call_core.tts "hello"`
  - Manual validation on macOS completed: STT transcribed live mic input and TTS playback succeeded through `afplay`

- **Phase 3: Portable MCP transport** — COMPLETE
  - `adapters/mcp_server.py` — FastMCP server exposing `call_listen()`, `call_speak()`, `call_end()`
  - Structured JSON tool contract:
    - `call_listen()` returns `status`, `text`, `error`
    - `call_speak()` / `call_end()` return `status`, `error`
  - Heartbeat progress notifications emitted every 5 seconds across idle listening and active recording
  - Error normalization implemented for mic permission/device failures, STT failures, TTS failures, and playback failures
  - Validated locally with mocked tool calls and a stdio MCP client calling `call_end()`
  - `requirements.txt` now includes `mcp[cli]` for SDK + local inspector/client tooling
  - Current repo `.venv` is Python 3.9.6, but the official `mcp` SDK requires Python 3.10+; use Python 3.11+ for phase 3 and phase 4A testing

- **Phase 4B: Claude Code skill + Claude install/config** — NOT STARTED (now first priority)
  - `commands/call.md`
  - Claude-specific MCP registration, timeout config, install steps

- **Phase 4A: Codex CLI skill + Codex install/config** — NOT STARTED (deferred)
  - `.agents/skills/call/SKILL.md`
  - `.agents/skills/call/agents/openai.yaml` — optional Codex metadata
  - Codex MCP registration + timeout config

**Why:** User wants any new agent or conversation to know exactly where to pick up.
**How to apply:** Check this memory before starting work. Update it as phases complete.
