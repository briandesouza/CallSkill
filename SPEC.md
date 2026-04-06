# call — Spec

A portable call mode for terminal coding agents. Codex CLI is the first host target. Claude Code CLI is planned as a later adapter. You speak, the agent listens, thinks, and speaks back. No keyboard needed after activation.

## How it works

1. User invokes the host adapter for call mode.
2. The host adapter switches the agent into conversational call mode.
3. Mic opens and listens for user speech.
4. When the user stops speaking, the audio is transcribed and returned to the agent.
5. The agent responds conversationally in short spoken-word style.
6. The response is spoken back via text-to-speech.
7. Mic opens again, waiting for the next utterance.
8. Repeat until the user says "end call" or "goodbye".
9. Conversation context is preserved in the same host session after the call ends.

## Architecture

**Approach: portable core + portable MCP transport + thin host adapters**

- `call_core/` owns recording, silence detection, STT, TTS, and playback.
- `adapters/mcp_server.py` exposes portable MCP tools that any host can use.
- Host adapters define invocation UX, prompt behavior, timeout config, and install steps for a specific environment.

Current priority is Codex CLI first. Claude Code CLI comes later as a thin adapter over the same core and MCP tool contract.

```text
Host adapter (Codex first, Claude later) + MCP server (portable tools)

Agent loop:
  call_listen() -> user speech -> STT -> text returned to agent
  Agent thinks, generates short response
  call_speak("response") -> TTS -> audio plays through speakers
  call_listen() -> repeat
```

**Why this approach over a wrapper script:**
- Stays inside the coding agent environment with full access to codebase, tools, and conversation history
- Keeps the audio implementation reusable across multiple hosts
- Preserves conversation context after the call ends
- Makes Codex-first delivery compatible with a later Claude adapter

## Portable MCP transport

### Tools

**`call_listen()`**
- Opens microphone and records audio
- Uses silence detection to determine when the user is done speaking
- Sends audio to ElevenLabs STT (Scribe) for transcription
- Returns transcribed text to the host agent
- Sends MCP progress notifications every 5-10 seconds to prevent host tool timeouts
- Returns `{"status": "silence", "text": ""}` if no speech is detected within 30 seconds
- Returns `{"error": "mic_permission_denied"}` if mic access is blocked

**`call_speak(text)`**
- Sends text to ElevenLabs TTS API
- Plays audio through speakers
- Blocks until playback finishes
- Returns when done

**`call_end()`**
- Cleans up any audio resources
- Returns confirmation

### Silence detection

Simple state machine using `webrtcvad` (Google's WebRTC Voice Activity Detection):

```text
IDLE (waiting for speech)
  | webrtcvad detects speech frames
  v
RECORDING (user is talking)
  | 2 seconds of non-speech frames
  v
DONE -> send audio to STT -> return text
```

Default silence threshold: 2 seconds. Start here, tune based on feedback.

`webrtcvad` classifies 20 ms audio frames as speech or non-speech. It is lightweight, requires no model download, and is well-tested.

### Timeout handling

Different hosts have different MCP timeout defaults. `call_listen()` can block much longer than a normal tool call.

**Portable requirements:**
1. The host adapter must configure a longer timeout for `call_listen()`. Recommended starting point: 5 minutes.
2. The MCP server must send progress notifications every 5-10 seconds during recording.
3. `call_listen()` should return silence after a 30-second max wait for speech start so the host adapter can immediately retry.

Host-specific timeout settings belong in the adapter layer, not in `call_core/` or the MCP server logic.

### Half-duplex turn-taking

- Mic is only open during `call_listen()`
- During the agent response and `call_speak()`, mic is closed
- No echo cancellation needed because mic and speaker are never active simultaneously
- No interruption handling in V0

## Shared conversation rules

These rules belong in the host adapter prompt, regardless of whether the host is Codex CLI or Claude Code CLI.

### Loop control

```text
CRITICAL: After EVERY call_speak(), immediately call call_listen() again.
The only exit is the user saying "end call" or "goodbye".
```

### Conversational behavior

- Short responses, 2-3 sentences unless the user asks for detail
- No markdown, bullet points, code blocks, or special formatting
- Refer to code concepts naturally
- Speak naturally, as in a real conversation
- The agent may read files, search code, and explore, but should discuss findings verbally
- Do not make code changes or write files unless the user explicitly asks for implementation
- If the user asks to implement something mid-call: "Sure, I'll do that after we end the call. Say 'end call' when you're ready."

### Onboarding (mic permissions)

```text
If call_listen() returns a permission error, tell the user:
"I need microphone access. You should see a permission popup from your terminal app - click Allow.
If not, go to System Settings > Privacy & Security > Microphone and enable it for your terminal."
Then try call_listen() again.
```

### On silence or empty returns

```text
If call_listen() returns empty or silence, the user has not spoken yet.
Call call_listen() again immediately. Do not comment on the silence.
```

## Host adapters

Host adapters are thin layers that set invocation UX, prompt behavior, install steps, and host-specific config. They should never reimplement audio logic or change the MCP tool contract.

### Phase 4A: Codex CLI adapter

- Provide a Codex skill at `.agents/skills/call/SKILL.md`
- Optionally add `.agents/skills/call/agents/openai.yaml` for UI metadata and MCP dependency hints
- Register the MCP server in Codex CLI and set a longer tool timeout
- Prefer explicit invocation via `$call` at first; allow implicit invocation later only if the trigger behavior is reliable
- Keep Codex-specific install and configuration steps separate from the portable MCP server

### Phase 4B: Claude Code CLI adapter

- Provide the Claude-side command or skill wrapper, currently planned as `commands/call.md`
- Apply Claude-specific timeout and installation steps in the adapter layer
- Reuse the same MCP tools and shared conversation rules from the Codex-first implementation
- Do not fork the audio logic or MCP semantics for Claude unless a host limitation forces it

## STT and TTS provider

**MVP: ElevenLabs for both**

- STT: ElevenLabs Scribe API (`POST /v1/speech-to-text`)
- TTS: ElevenLabs TTS API (`POST /v1/text-to-speech/{voice_id}`)
- User provides their own API key via `ELEVENLABS_API_KEY`
- STT default model: `scribe_v2`
- TTS default voice: `tMvyQtpCVQ0DkixuYm6J`, overridable via `ELEVENLABS_VOICE_ID`
- TTS default model: `eleven_flash_v2_5`, overridable via `ELEVENLABS_TTS_MODEL_ID`
- V0 playback uses MP3 output (`mp3_44100_128`) plus macOS `afplay`

**Why ElevenLabs for MVP:**
- Both STT and TTS from one provider, one API key
- Simple HTTP calls
- High-quality output
- No model downloads
- Fast setup for users

**Future: swappable providers** via simple interface:

```python
class STTProvider:
    def transcribe(self, audio_bytes: bytes) -> str: ...

class TTSProvider:
    def synthesize(self, text: str) -> bytes: ...
```

Later options may include local Whisper and Piper, OpenAI, and other providers.

## Project structure

```text
call/
├── SPEC.md
├── CLAUDE.md
├── memory/
│   └── implementation_progress.md
├── call_core/
│   ├── __init__.py
│   ├── recorder.py
│   ├── stt.py
│   ├── tts.py
│   └── audio.py
├── adapters/
│   └── mcp_server.py
├── .agents/
│   └── skills/
│       └── call/
│           ├── SKILL.md
│           └── agents/
│               └── openai.yaml
├── commands/
│   └── call.md
├── requirements.txt
└── pyproject.toml
```

Not every adapter file exists yet. The important boundary is:
- `call_core/` stays backend-agnostic
- `adapters/mcp_server.py` stays host-neutral
- Codex and Claude integration assets live in separate adapter layers

## Implementation phases

- **Phase 1: Recorder**
  - `call_core/recorder.py`
- **Phase 2: Core speech providers + playback**
  - `call_core/stt.py`
  - `call_core/tts.py`
  - `call_core/audio.py`
- **Phase 3: Portable MCP transport**
  - `adapters/mcp_server.py`
- **Phase 4A: Codex CLI skill + Codex install/config**
  - `.agents/skills/call/SKILL.md`
  - Codex MCP registration and timeout configuration
- **Phase 4B: Claude Code skill + Claude install/config**
  - `commands/call.md`
  - Claude-specific install and timeout configuration

## Latency budget (per turn)

| Step | Estimate |
|---|---|
| Silence detection buffer | 2s after user stops |
| ElevenLabs STT | 0.5-1.5s |
| MCP tool return overhead | ~0.5s |
| Agent thinking + response | 1-3s |
| MCP tool call overhead | ~0.5s |
| ElevenLabs TTS | 0.5-1s |
| **Total after user stops speaking** | **~5-8s** |

Acceptable for conversational use. Streaming TTS could shave 1-2 seconds later.

## MVP scope (V0)

**Current target:**
- Phase 1 through Phase 3
- Phase 4A Codex CLI adapter
- ElevenLabs STT + TTS
- Silence detection via `webrtcvad`
- Half-duplex turn-taking
- macOS support
- macOS playback via `afplay`
- Basic README and setup documentation

**Planned later:**
- Phase 4B Claude Code CLI adapter

**Out of scope for V0:**
- Voice activity detection with interruption
- Local model support such as Whisper or Piper
- Echo cancellation
- Streaming TTS
- Linux support
- Configurable silence threshold
- Multiple ElevenLabs voice options

## Implementation order

1. `call_core/recorder.py` - mic recording + silence detection with `webrtcvad`
2. `call_core/stt.py` - ElevenLabs STT integration
3. `call_core/tts.py` - ElevenLabs TTS integration
4. `call_core/audio.py` - audio playback
5. `adapters/mcp_server.py` - portable MCP server wrapping the core tools
6. `.agents/skills/call/SKILL.md` - Codex CLI skill prompt
7. Codex MCP registration and timeout configuration
8. `commands/call.md` - Claude Code adapter
9. Claude-specific install and timeout configuration
10. README and end-to-end testing

## Key design decisions log

| Decision | Choice | Why |
|---|---|---|
| Architecture | Portable core + portable MCP transport + host adapters | Enables Codex first, Claude later, without rewriting audio logic |
| Host priority | Codex CLI first | Fastest path to first integrated host while keeping Claude viable later |
| MCP tool contract | Stable across hosts | Minimizes adapter-specific branching |
| Naming | "call" not "voice" | Avoid confusion with existing voice features in host tools |
| STT/TTS provider | ElevenLabs (MVP) | Simplest integration, one API key, good quality |
| Silence detection | `webrtcvad` | Lightweight, no model downloads, reliable |
| Turn-taking | Half-duplex, auto silence detection | Hands-free UX without concurrency complexity |
| Default silence threshold | 2 seconds | Balance between responsiveness and mid-thought pauses |
| During response | Mic off, ignore input | Avoids echo and interruption complexity for V0 |
| Code changes during call | Disabled unless explicitly asked | Keeps call conversational and exploratory |
| Loop recovery | Strong prompting plus silence retry | Sufficient for MVP, revisit if needed |
| Text formatting for TTS | Handled in adapter prompt | Avoids programmatic markdown stripping |
| Python for core and MCP | Yes | Best audio ecosystem |
