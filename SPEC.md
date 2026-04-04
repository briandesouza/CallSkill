# claude-call — Spec

A Claude Code skill that lets you have a hands-free voice conversation with Claude Code in your terminal. You speak, Claude listens, thinks, and speaks back. No keyboard needed after activation.

## How it works

1. User opens Claude Code, types `/call`
2. Claude enters conversational voice mode
3. Mic opens, listens for user speech
4. When user stops speaking (silence detection), the audio is transcribed and sent to Claude
5. Claude responds conversationally (short, spoken-word style)
6. Response is spoken back via text-to-speech
7. Mic opens again, waiting for the next utterance
8. Repeat until user says "end call"
9. Conversation context is preserved — user can continue in normal keyboard mode

## Architecture

**Approach: MCP Server + Claude Code Skill**

The voice I/O lives in an MCP server. The `/call` skill sets Claude into conversational mode and instructs it to use the MCP tools in a loop. Claude stays in the driver's seat — it can still read files, search code, explore the codebase, and reference the full conversation history.

```
/call skill (sets behavior) + MCP server (provides tools)

Claude's loop:
  call_listen() → user speech → STT → text returned to Claude
  Claude thinks, generates short response
  call_speak("response") → TTS → audio plays through speakers
  call_listen() → repeat
```

**Why this approach over a wrapper script:**
- Stays inside Claude Code — full access to codebase, tools, conversation history
- User can say "look at the auth module" and Claude can actually read it
- Conversation context preserved after the call ends
- Natural integration point for Claude Code users

## MCP Server

### Tools

**`call_listen()`**
- Opens microphone, records audio
- Uses silence detection to determine when user is done speaking
- Sends audio to ElevenLabs STT (Scribe) for transcription
- Returns transcribed text to Claude
- Sends MCP progress notifications every 5-10 seconds to prevent timeout
- Returns `{"status": "silence", "text": ""}` if no speech detected within 30 seconds (Claude should call again)
- Returns `{"error": "mic_permission_denied"}` if mic access is blocked

**`call_speak(text)`**
- Sends text to ElevenLabs TTS API
- Plays audio through speakers (blocking — waits until playback finishes)
- Returns when done

**`call_end()`**
- Cleanup (close any audio resources)
- Returns confirmation

### Silence detection

Simple state machine using `webrtcvad` (Google's WebRTC Voice Activity Detection):

```
IDLE (waiting for speech)
  │ webrtcvad detects speech frames
  ▼
RECORDING (user is talking)
  │ 2 seconds of non-speech frames
  ▼
DONE → send audio to STT → return text
```

Default silence threshold: 2 seconds. Start here, tune based on feedback.

`webrtcvad` classifies 20ms audio frames as speech/not-speech. Lightweight, no ML model to download, well-tested.

### MCP timeout handling

Claude Code's default MCP tool timeout is 10 seconds. `call_listen()` can block for much longer.

**Solution:**
1. Install script sets `MCP_TIMEOUT=300000` (5 minutes) in Claude Code settings
2. MCP server sends progress notifications every 5-10 seconds during recording
3. `call_listen()` has a 30-second max-wait for speech start — returns empty if no speech, Claude calls again

### Half-duplex turn-taking

- Mic is ONLY open during `call_listen()`
- During Claude's response and `call_speak()`, mic is closed
- No echo cancellation needed (mic and speaker never active simultaneously)
- No interruption handling in V0

## The /call Skill

The skill file (`call.md`) sets Claude's behavior for the duration of the call.

### Key prompt elements

**Loop control:**
```
CRITICAL: After EVERY call_speak(), you MUST immediately call call_listen().
There are ZERO exceptions. The ONLY exit is the user saying "end call" or "goodbye".
```

**Conversational behavior:**
- Short responses, 2-3 sentences unless user asks for detail
- No markdown, bullet points, code blocks, or special formatting
- Refer to code concepts naturally ("the auth handler" not "auth_handler.py")
- Speak naturally, as in a real conversation
- CAN read files, search code, explore — just discuss findings verbally
- Do NOT make code changes, write files, or edit anything unless user explicitly says "go ahead", "do it", or "implement that"
- If user asks to implement something: "Sure, I'll do that after we end the call. Say 'end call' when you're ready."

**Onboarding (mic permissions):**
```
If call_listen() returns a permission error, guide the user:
"I need microphone access. You should see a permission popup from your terminal app —
click Allow. If not, go to System Settings > Privacy & Security > Microphone
and enable it for your terminal."
Then try call_listen() again.
```

**On silence/empty returns:**
```
If call_listen() returns empty/silence, the user hasn't spoken yet.
Call call_listen() again immediately. Do not comment on the silence.
```

## STT and TTS Provider

**MVP: ElevenLabs for both**

- STT: ElevenLabs Scribe API (`POST /v1/speech-to-text`)
- TTS: ElevenLabs TTS API (`POST /v1/text-to-speech/{voice_id}`)
- User provides their own API key via `ELEVENLABS_API_KEY` env var

**Why ElevenLabs for MVP:**
- Both STT and TTS from one provider, one API key
- Simple HTTP calls (~20 lines of code)
- High quality output
- No model downloads
- Fast setup for users

**Future: swappable providers** via simple interface:
```python
class STTProvider:
    def transcribe(self, audio_bytes: bytes) -> str: ...

class TTSProvider:
    def synthesize(self, text: str) -> bytes: ...
```
Later add: local Whisper + Piper, OpenAI, etc.

## Project structure

```
claude-call/
├── README.md                     # for users: what it does, install, demo GIF
├── LICENSE                       # MIT
├── CONTRIBUTING.md               # for contributors: setup, PR guidelines
├── SPEC.md                       # this file: design decisions and architecture
├── CLAUDE.md                     # instructions for Claude Code agents working on this
├── .env.example                  # ELEVENLABS_API_KEY=your_key_here
│
├── call_core/                    # backend-agnostic audio engine
│   ├── __init__.py
│   ├── recorder.py               # mic recording + silence detection (webrtcvad)
│   ├── stt.py                    # ElevenLabs STT
│   ├── tts.py                    # ElevenLabs TTS
│   └── audio.py                  # audio playback utilities
│
├── adapters/
│   └── mcp_server.py             # MCP server exposing call_listen, call_speak, call_end
│
├── commands/
│   └── call.md                   # the /call skill for Claude Code
│
├── requirements.txt              # Python dependencies
├── pyproject.toml                # package metadata
└── install.sh                    # one-command setup
```

`call_core/` is deliberately backend-agnostic — no Claude Code or MCP concepts. This allows future reuse for a standalone CLI wrapper that supports Codex or other tools.

## Latency budget (per turn)

| Step | Estimate |
|---|---|
| Silence detection buffer | 2s after user stops |
| ElevenLabs STT | 0.5-1.5s |
| MCP tool return overhead | ~0.5s |
| Claude thinking + response | 1-3s |
| MCP tool call overhead | ~0.5s |
| ElevenLabs TTS | 0.5-1s |
| **Total after user stops speaking** | **~5-8s** |

Acceptable for conversational use. Streaming TTS (future optimization) could shave 1-2s.

## MVP scope (V0)

**In scope:**
- MCP server with `call_listen()`, `call_speak()`, `call_end()`
- `/call` skill with conversational mode + loop instructions
- ElevenLabs STT + TTS
- Silence detection via webrtcvad
- Half-duplex (mic off during response)
- macOS support
- Install script
- Basic README

**Out of scope (future versions):**
- Voice Activity Detection with interruption (V1)
- Local model support — Whisper, Piper (V1)
- Echo cancellation (V1)
- Streaming TTS (V1)
- Standalone CLI for Codex/other tools (V2)
- Linux support (V1)
- Configurable silence threshold (V1)
- Multiple ElevenLabs voice options (V1)

## Implementation order

1. **call_core/recorder.py** — mic recording + silence detection with webrtcvad
2. **call_core/stt.py** — ElevenLabs STT integration
3. **call_core/tts.py** — ElevenLabs TTS integration
4. **call_core/audio.py** — audio playback
5. **adapters/mcp_server.py** — MCP server wrapping the core tools
6. **commands/call.md** — the /call skill prompt
7. **install.sh** — setup script
8. **README.md** — user-facing docs
9. **Testing + iteration** — end-to-end testing of the full loop

## Key design decisions log

| Decision | Choice | Why |
|---|---|---|
| Architecture | MCP server + skill (not wrapper) | Stays inside Claude Code, preserves context |
| Naming | "call" not "voice" | Avoid confusion with Claude's voice mode |
| STT/TTS provider | ElevenLabs (MVP) | Simplest integration, one API key, good quality |
| Silence detection | webrtcvad | Lightweight, no model downloads, reliable |
| Turn-taking | Half-duplex, auto silence detection | Hands-free UX without concurrency complexity |
| Default silence threshold | 2 seconds | Balance between responsiveness and mid-thought pauses |
| During response | Mic off, ignore input | Avoids echo/interruption complexity for V0 |
| Code changes during call | Disabled unless explicitly asked | Keeps call conversational and exploratory |
| Loop recovery | Strong prompting, no special mechanism | Sufficient for MVP, revisit if needed |
| macOS mic permissions | Handled via skill onboarding prompt | No extra code, Claude guides user through it |
| Text formatting for TTS | Handled via skill prompt (conversational style) | No programmatic markdown stripping needed |
| License | MIT | Most permissive, contributor-friendly |
| Python (MCP server) | Yes | Best audio ecosystem (sounddevice, webrtcvad) |
