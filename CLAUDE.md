# call

## What this project is

A portable call mode for terminal coding agents. The current implementation priority is Codex CLI first. Claude Code CLI is planned later as a thin adapter over the same core and MCP transport.

## Read first

Read `SPEC.md` for the full design spec. That file is the source of truth for architecture, phase boundaries, and host-adapter responsibilities.

## Architecture summary

- **Core library** (`call_core/`) handles mic recording, silence detection, STT, TTS, and playback
- **Portable MCP transport** (`adapters/mcp_server.py`) exposes `call_listen()`, `call_speak()`, and `call_end()`
- **Codex adapter** will live in `.agents/skills/call/`
- **Claude adapter** is planned later and should stay thin

## Key constraints

- Use "call" terminology everywhere, never "voice"
- `call_core/` must stay backend-agnostic: no Codex CLI, Claude Code, or MCP host config inside it
- `adapters/mcp_server.py` must stay host-neutral: expose only the portable tool contract and audio behavior, not Claude-specific prompts or timeout configuration
- Current adapter priority is Codex CLI first. Do not bias phases 2-4A toward Claude-specific workflow assumptions
- Half-duplex: mic is only open during `call_listen()`, never during `call_speak()`
- The MCP server must send progress notifications every 5-10 seconds during `call_listen()`
- Silence threshold defaults to 2 seconds
- Python is the implementation language for the audio core and MCP transport

## Implementation phases

1. `call_core/recorder.py` - recorder
2. `call_core/stt.py`, `call_core/tts.py`, `call_core/audio.py` - core speech providers + playback
3. `adapters/mcp_server.py` - portable MCP transport
4. `.agents/skills/call/` - Codex CLI skill + Codex install/config
5. `commands/call.md` - Claude Code skill + Claude install/config

## Dependencies

- `sounddevice` - mic access
- `webrtcvad` - silence detection
- `requests` - ElevenLabs API calls
- `mcp` - MCP server SDK
- `afplay` - macOS playback for V0

## Testing

Test each layer independently:
- `call_core/recorder.py` - can record and detect silence
- `call_core/stt.py` - can transcribe audio via ElevenLabs
- `call_core/tts.py` - can synthesize and return audio
- `adapters/mcp_server.py` - tools return expected responses without host-specific branching
- End-to-end - Codex CLI first, Claude adapter later
