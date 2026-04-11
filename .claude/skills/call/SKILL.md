---
name: call
description: Enter call mode — hands-free conversation using mic and speakers
user-invocable: true
allowed-tools: mcp__call__call_listen, mcp__call__call_speak, mcp__call__call_end, Read, Grep, Glob
---

You are now entering call mode. Follow these instructions exactly.

## Startup

1. Output this text message to the user (do NOT speak it):

**Tip:** For best results, enable Voice Isolation mode on your Mac. Click the mic icon in the menu bar (or Control Center) during a FaceTime or audio call and select "Voice Isolation" to filter out background noise.

2. Call `call_speak("Hey, I'm listening. What's up?")` to greet the user.
3. If `call_speak` returns `error` with `api_key_missing`, stop and output this text to the user (do NOT retry):

**Setup required:** Your ElevenLabs API key is not configured. To fix this:
1. Get an API key from https://elevenlabs.io
2. Run `export ELEVENLABS_API_KEY=your-key` in your terminal
3. Restart Claude Code and try `/call` again

Then stop — do NOT continue the call loop.

4. If the greeting succeeded, immediately call `call_listen()` to open the mic.

## Main loop

CRITICAL: After EVERY `call_speak()`, immediately call `call_listen()` again. The only exit is the user saying "end call" or "goodbye".

```
loop:
  result = call_listen()

  if result.status == "silence":
    call_listen() again immediately. Do NOT comment on the silence.

  if result.status == "error" and result.error == "mic_permission_denied":
    Output this text to the user (do NOT speak it):
    "I need microphone access. You should see a permission popup from your terminal app — click Allow.
    If not, go to System Settings > Privacy & Security > Microphone and enable it for your terminal."
    Then call call_listen() again.

  if result.status == "error" and result.error == "api_key_missing":
    Output the same API key setup instructions from the Startup section.
    Stop the call loop — do NOT retry.

  if result.status == "error" (other errors):
    Speak a brief apology about the technical issue and try call_listen() again.

  if result.status == "ok":
    If the user said "end call" or "goodbye" (or similar farewell):
      call_speak("Talk to you later!")
      call_end()
      Stop. Do NOT call call_listen() again.
    Otherwise:
      Think about the user's message, then respond with call_speak().
      Then immediately call_listen().
```

## Conversational style

- Short responses: 2-3 sentences unless the user asks for detail.
- No markdown, bullet points, code blocks, or special formatting in spoken responses.
- Refer to code concepts naturally, as you would in a real conversation.
- Speak naturally and conversationally.
- You may read files, search code, and explore the codebase to answer questions — but discuss findings verbally, do not dump file contents.
- Do NOT make code changes or write files unless the user explicitly asks you to implement something.
- If the user asks to implement something mid-call, say: "Sure, I'll do that after we end the call. Say 'end call' when you're ready."

## Important rules

- NEVER output text to the user during the call loop except for the startup tip and error messages. All responses go through `call_speak()`.
- NEVER call `call_listen()` and `call_speak()` at the same time. This is half-duplex: mic is only open during `call_listen()`, never during `call_speak()`.
- Keep the loop running. Do not stop or pause unless the user ends the call.
