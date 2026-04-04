# claude-call

## What this project is

A Claude Code skill (`/call`) that enables hands-free voice conversations with Claude Code. User speaks, Claude listens via silence detection, thinks, and speaks back using text-to-speech. No keyboard needed after activation.

## Read first

Read `SPEC.md` for the full design spec — architecture, design decisions, MVP scope, and implementation order. That is the source of truth for this project.

## Architecture summary

- **MCP server** (`adapters/mcp_server.py`) exposes three tools: `call_listen()`, `call_speak()`, `call_end()`
- **Skill file** (`commands/call.md`) sets Claude into conversational loop mode
- **Core library** (`call_core/`) handles mic recording, silence detection, STT, TTS — backend-agnostic, no MCP concepts
- **STT/TTS**: ElevenLabs APIs (MVP). Provider interface designed for future swapping.

## Key constraints

- Use "call" terminology everywhere, never "voice" (avoids confusion with Claude's voice mode)
- `call_core/` must stay backend-agnostic — no Claude Code or MCP imports. This enables future standalone CLI support.
- Half-duplex: mic is ONLY open during `call_listen()`. Never during `call_speak()`.
- MCP server must send progress notifications every 5-10 seconds during `call_listen()` to prevent Claude Code timeout.
- Silence threshold: 2 seconds default.
- Python for the MCP server (best audio ecosystem).

## Implementation order

1. `call_core/recorder.py` — mic + webrtcvad silence detection
2. `call_core/stt.py` — ElevenLabs STT
3. `call_core/tts.py` — ElevenLabs TTS
4. `call_core/audio.py` — audio playback
5. `adapters/mcp_server.py` — MCP server
6. `commands/call.md` — skill prompt
7. `install.sh` — setup script
8. `README.md` — user docs

## Dependencies

- `sounddevice` — mic access
- `webrtcvad` — silence detection
- `requests` — ElevenLabs API calls
- `mcp` — MCP server SDK
- `numpy` — audio frame processing

## Testing

Test each layer independently:
- `call_core/recorder.py` — can record and detect silence
- `call_core/stt.py` — can transcribe audio via ElevenLabs
- `call_core/tts.py` — can synthesize and return audio
- `adapters/mcp_server.py` — tools return expected responses
- End-to-end — full `/call` loop works in Claude Code
