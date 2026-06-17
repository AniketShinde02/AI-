# IRIS_VOICE_BLUEPRINT.md
## Why IRIS Feels Instant — Architecture Dissection

*Note: IRIS source code was previously audited and summarized in IRIS_COMPARISON.md. This section synthesizes those findings with Nexus's current architecture to explain the perceived latency difference.*

### The Core Reason IRIS Feels Instant

IRIS uses **Gemini Live** (`gemini-2.5-flash-native-audio-preview`) via a **true bidirectional WebSocket**, not a REST API. Nexus uses `generateContent` via REST API. This is the single biggest difference.

**Nexus (Current) Pipeline:**
```
User speaks → VAD end → STT (Groq, full upload) → LLM → TTS (REST, full generation) → Audio
Total: 10-18 seconds
```

**IRIS/Gemini Live Pipeline:**
```
User speaks → Raw PCM sent continuously to Gemini Live WebSocket
Gemini Live: STT + LLM + TTS in ONE continuous stream
Audio chunks returned immediately as the model speaks
Total: 0.3-0.8 seconds TTFA
```

---

### Nexus's Own Gemini Live Experiment (Confirmed Existing)
**File:** `d:\AI\backend\voice_agent\experimental\gemini_live_voice.py`

The experiment already exists in Nexus and implements the correct pattern:

```python
# Line 57: True bidirectional async WS connection
async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-preview-12-2025", config=config) as session:

# Line 85-92: Raw PCM sent chunk-by-chunk (no VAD wait, no batch upload)
await session.send(
    input=types.LiveClientRealtimeInput(
        media_chunks=[types.Blob(mime_type="audio/pcm;rate=16000", data=pcm_data)]
    )
)

# Line 101-126: Audio returned immediately as model generates it
async for response in session.receive():
    ...
    pcm_data = part.inline_data.data
    await websocket.send_json({"type": "audio_chunk", "data": out_b64})
```

This is the correct architecture. It eliminates:
- The 12.8s preroll buffer problem (no VAD needed for Gemini Live)
- The 3-4s Groq STT upload delay (no STT needed)
- The 4-7s Gemini TTS REST latency (audio streams as the model speaks)

### Why Gemini Live Isn't Yet the Primary in Nexus
1. The experiment file is in `experimental/`, not wired into the main `ws_main.py` path.
2. Rate limits on Gemini free tier make it risky as the only provider.
3. No interruption handling exists in the experiment.
4. No fallback logic exists if the Gemini Live session drops.

### Gemini Live Constraints Observed in Code
- **Model:** `gemini-2.5-flash-native-audio-preview-12-2025` — This is a preview model, subject to change.
- **Audio Input Format:** `audio/pcm;rate=16000` (matches Nexus's current 16kHz capture)
- **Audio Output:** Raw PCM inline_data, needs format detection (may be 24kHz)
- **No barge-in/interruption logic** in the experiment file.
- **No reconnection logic** — session dies on any exception, no retry.
- **No conversation history** — stateless per-connection only.

### What IRIS Does That Nexus Does Not (Yet)
1. **Continuous Streaming:** Audio bytes are sent to Gemini Live continuously, not after VAD endpoint.
2. **No STT Step:** The LLM handles speech-to-understanding natively.
3. **Interruption:** IRIS cancels the ongoing response when new audio energy is detected.
4. **Tool Calling Integration:** IRIS intercepts Gemini Live `tool_call` events and executes them server-side.

### Answer: Why Does IRIS Feel Instant?
Because IRIS eliminated the three biggest latency contributors (VAD batch wait, Groq STT upload, Gemini TTS REST generation) by routing raw PCM directly to Gemini Live's combined STT+LLM+TTS pipeline. The result is audio-in → audio-out in under 1 second.
