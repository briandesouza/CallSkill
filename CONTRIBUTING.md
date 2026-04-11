# Contributing

Thanks for your interest in call mode. This guide covers what you need to get started.

## Dev setup

1. **Python 3.11** is required (`webrtcvad` and the `mcp` SDK need it).

   ```sh
   brew install python@3.11  # macOS
   ```

2. **Create the virtual environment** at `.venv311/` (the MCP config expects this path):

   ```sh
   python3.11 -m venv .venv311
   .venv311/bin/pip install -r requirements.txt
   ```

3. **Set your ElevenLabs API key:**

   ```sh
   export ELEVENLABS_API_KEY=your-key-here
   ```

   See `.env.example` for all available environment variables.

## Architecture boundaries

The codebase has three layers with strict separation:

| Layer | Path | Rule |
|---|---|---|
| Core library | `call_core/` | Backend-agnostic. No references to Claude Code, Codex, MCP hosts, or host-specific config. |
| MCP transport | `adapters/mcp_server.py` | Host-neutral. Exposes the portable tool contract (`call_listen`, `call_speak`, `call_end`). No host-specific prompts or timeout config. |
| Host adapters | `.claude/skills/call/`, `.mcp.json` | Claude Code-specific invocation, prompts, and config. Other hosts get their own adapter directories. |

When making changes, keep code in the right layer. If you're unsure, check `SPEC.md` for the full design spec.

## Testing each layer

There's no automated test suite yet. Test manually:

```sh
# Recorder — records from mic, stops on 2s silence
.venv311/bin/python -m call_core.recorder

# STT — records then transcribes via ElevenLabs
.venv311/bin/python -m call_core.stt

# TTS — synthesizes and plays speech
.venv311/bin/python -m call_core.tts "hello from call mode"

# MCP server — start the server (Ctrl+C to stop)
.venv311/bin/python -m adapters.mcp_server

# End-to-end — open Claude Code in the project directory and run /call
```

## Temporary files

Put all scratch, debug, and test files in `scratch/`. That directory is gitignored. Never create temp files in the project root.

## Pull requests

- Keep PRs focused — one concern per PR.
- Test your changes manually with the commands above before submitting.
- Follow existing code patterns. Read `CLAUDE.md` for project conventions.
- Use "call" terminology, never "voice".
