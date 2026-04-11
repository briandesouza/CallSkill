# call

Talk to Claude Code hands-free. You speak, Claude listens, thinks, and speaks back. No keyboard needed after `/call`.

```
You: /call
Claude (speaking): "Hey, I'm listening. What's up?"
You (speaking):    "What does the recorder module do?"
Claude (speaking): "It captures audio from your mic and uses WebRTC voice activity
                    detection to figure out when you've stopped talking. Once it
                    detects about two seconds of silence, it stops recording and
                    hands the audio off for transcription."
You (speaking):    "End call"
Claude (speaking): "Talk to you later!"
```

Claude can still read files, search code, and explore your codebase during the call. Conversation context is preserved after the call ends, so you can continue working in the same session.

## How it works

```
You speak -> mic records -> silence detected -> ElevenLabs STT -> text to Claude
-> Claude thinks -> response text -> ElevenLabs TTS -> audio plays -> mic reopens
```

The call is half-duplex: the mic is only open while Claude is listening, never while Claude is speaking. This avoids echo issues and keeps things simple.

## Requirements

- **macOS** (V0 uses the built-in `afplay` command for audio playback)
- **Python 3.11** (`webrtcvad` may not compile on other versions)
- **Claude Code CLI**
- **ElevenLabs account** with an API key (free tier works)

## Setup

### Quick setup (let Claude do it)

Open Claude Code in this project directory and say:

> Read the README and set up call mode for me.

Claude will create the virtual environment, install dependencies, and walk you through the API key step. Skip to [Add your ElevenLabs API key](#2-add-your-elevenlabs-api-key) if Claude asks you to configure it.

### Manual setup

#### 1. Clone and enter the repo

```sh
git clone https://github.com/briandesouza/CallSkill.git
cd CallSkill
```

#### 2. Add your ElevenLabs API key

Get a free API key from [elevenlabs.io](https://elevenlabs.io) and add it to your shell profile so it's available every time you open a terminal:

```sh
echo 'export ELEVENLABS_API_KEY=your-key-here' >> ~/.zshrc
source ~/.zshrc
```

Without this, call mode cannot reach the speech API and will show a setup error on first use.

#### 3. Create the Python virtual environment

The MCP server configuration (`.mcp.json`) expects the virtual environment at `.venv311/`. Create it with Python 3.11 specifically:

```sh
python3.11 -m venv .venv311
.venv311/bin/pip install -r requirements.txt
```

If `python3.11` isn't found, install it first:

```sh
brew install python@3.11
```

#### 4. Start Claude Code

```sh
claude
```

Open Claude Code **inside this project directory**. It auto-discovers the `.mcp.json` file at the project root, which registers the call MCP server. If you open Claude Code from a different directory, it won't find the server.

You should see the `call` MCP server listed when Claude Code starts. If it fails to connect, check that `.venv311/` exists and has the dependencies installed.

### Global install (use from any directory)

The default setup only works when Claude Code is opened from the project directory. To make `/call` available in every Claude Code session, copy the MCP config and skill to your user-level `~/.claude/` directory.

Replace `/path/to/callMode` below with the absolute path where you cloned this repo.

**1. Create `~/.claude/.mcp.json`**

If this file doesn't exist yet, create it. If it already exists, add the `call` entry to the existing `mcpServers` object.

```json
{
  "mcpServers": {
    "call": {
      "type": "stdio",
      "command": "/path/to/callMode/.venv311/bin/python",
      "args": ["-m", "adapters.mcp_server"],
      "env": {
        "ELEVENLABS_API_KEY": "${ELEVENLABS_API_KEY}",
        "PYTHONPATH": "/path/to/callMode"
      }
    }
  }
}
```

The key differences from the project-level config: absolute path to the venv Python, and `PYTHONPATH` so the module resolves from any working directory.

**2. Copy the skill**

```sh
mkdir -p ~/.claude/skills/call
cp /path/to/callMode/.claude/skills/call/SKILL.md ~/.claude/skills/call/SKILL.md
```

**3. Restart Claude Code**

Open Claude Code from any directory. You should see the `call` MCP server listed on startup, and `/call` should be available.

If you have both the global and project-level configs, they won't conflict — they use the same server name, and the project-level config takes precedence when you're in the project directory.

## Usage

1. Type `/call` to start a call
2. Speak naturally — Claude listens, thinks, and speaks back
3. Say **"end call"** or **"goodbye"** to stop
4. Your conversation continues in the same session after the call ends

During a call, Claude can read your files and search your codebase to answer questions, but it won't make code changes unless you explicitly ask. If you ask to implement something mid-call, Claude will offer to do it after the call ends.

**Tip:** For best results on Mac, enable Voice Isolation mode. Click the mic icon in the menu bar or Control Center and select "Voice Isolation" to filter out background noise.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `ELEVENLABS_API_KEY` | Yes | — | Your ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | No | `tMvyQtpCVQ0DkixuYm6J` | ElevenLabs voice to use for TTS |
| `ELEVENLABS_TTS_MODEL_ID` | No | `eleven_flash_v2_5` | ElevenLabs TTS model |

Set optional variables the same way as the API key:

```sh
echo 'export ELEVENLABS_VOICE_ID=your-voice-id' >> ~/.zshrc
source ~/.zshrc
```

Browse available voices at [elevenlabs.io/voices](https://elevenlabs.io/voices).

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `api_key_missing` | `ELEVENLABS_API_KEY` not set or not visible to the MCP server | Run `echo $ELEVENLABS_API_KEY` in your terminal. If empty, add the export to `~/.zshrc`, run `source ~/.zshrc`, then **restart Claude Code** so the MCP server picks up the new value. |
| `mic_permission_denied` | Your terminal app isn't authorized for microphone access | Go to **System Settings > Privacy & Security > Microphone** and enable your terminal app (Terminal, iTerm2, etc.). You may see a popup on first use — click Allow. |
| `mic_unavailable` | No microphone found or mic is in use by another app | Check that a mic is connected and not exclusively held by another application. |
| `stt_failed` | ElevenLabs speech-to-text returned an error | Verify your API key is valid and check [ElevenLabs status](https://status.elevenlabs.io). |
| `tts_failed` | ElevenLabs text-to-speech returned an error | Same as above. |
| `playback_failed` | `afplay` failed to play audio | Check that macOS volume is not muted. Test manually: `afplay /System/Library/Sounds/Ping.aiff` |
| MCP server won't start | Virtual environment missing or dependencies not installed | Verify `.venv311/` exists: `ls .venv311/bin/python`. If not, re-run the venv setup steps. |
| `pip install` fails on `webrtcvad` | Compilation error, wrong Python version | Use Python 3.11 specifically. If still failing, install Xcode command line tools: `xcode-select --install` |

## Limitations

This is V0. Current limitations:

- **macOS only** — playback uses `afplay`, which is macOS-specific
- **No interrupting** — you can't cut Claude off mid-sentence (half-duplex)
- **~5-8 second latency per turn** — silence detection + STT + thinking + TTS adds up
- **ElevenLabs only** — no local or offline speech models yet
- **No streaming TTS** — the full response is synthesized before playback starts
- **No configurable silence threshold** — fixed at 2 seconds

## Security

Your ElevenLabs API key is read from the shell environment at runtime via the `${ELEVENLABS_API_KEY}` interpolation in `.mcp.json`. It is never stored in any committed file. Do not commit `.env` files or hardcode your key.

## Architecture

```
call/
├── call_core/           # Portable audio core (no host dependencies)
│   ├── recorder.py      # Mic recording + WebRTC VAD silence detection
│   ├── stt.py           # ElevenLabs speech-to-text
│   ├── tts.py           # ElevenLabs text-to-speech
│   └── audio.py         # Audio clip playback (afplay on macOS)
├── adapters/
│   └── mcp_server.py    # MCP transport — exposes call_listen, call_speak, call_end
├── .claude/
│   └── skills/call/     # Claude Code skill (invoked via /call)
└── .mcp.json            # MCP server registration (auto-discovered by Claude Code)
```

`call_core/` is backend-agnostic — it knows nothing about Claude Code or MCP. `adapters/mcp_server.py` is host-neutral — it exposes the portable tool contract without host-specific logic. The Claude Code skill and `.mcp.json` are the only Claude-specific pieces.

See [SPEC.md](SPEC.md) for the full design spec, including the MCP tool contract, error codes, and design decisions.

## License

[MIT](LICENSE)
