# Nexus Final Voice System Audit & State of the System

## 1. What currently works?
- **Web Microphone Capture**: `voice-processor.js` correctly records, buffers, and dispatches 16kHz audio over WebSocket.
- **WebSocket Streaming**: Stable two-way streaming.
- **Speech-to-Text (STT)**: Groq Whisper implementation is exceptionally fast and accurate.
- **LLM Streaming**: Groq/Gemini LLM streams text chunks seamlessly while handling `<think>` tags.
- **Text-to-Speech (TTS)**: Gemini 2.5 TTS is active, fast, and generates valid Base64 PCM.

## 2. What is broken?
- **VAD (Voice Activity Detection) Lockups**: Fixed during this audit via threshold tuning and a hard 7-second timeout, but previously caused infinite `LISTENING` loops due to background hum.
- **TTS Router Contract**: Fixed during this audit (`isinstance(dict)` check), but previously the router leaked metadata objects into the audio processing loop, crashing the worker.
- **Frontend Fetch Error**: The frontend `NexusContext.tsx` is attempting to fetch chat history from `localhost:8001/api/history/` but it fails with CORS/500 errors.

## 3. What is redundant?
- Local Python packages like `kokoro-onnx` and `faster-whisper`.
- Heavy ML tooling (`vision-agents`) loaded into memory but not actively wired to Voice events.
- Multiple legacy test scripts polling different providers.

## 4. What is experimental?
- Agent automation (`app/agents`).
- Vision integration.
- Tool Calling (Tools exist but LLM voice prompt is not structured to invoke them predictably).

## 5. What is blocking production?
- **Code Organization (`ws_main.py` God Class)**: Over 1,000 lines of concurrent logic. A single unhandled exception in one queue brings down the entire pipeline.
- **Lack of Authentication**: WebSocket is unprotected and open.

## 6. What should be built next?
1. Split `ws_main.py` into smaller, testable concurrency modules.
2. Fix the `/api/history/` fetch error on the frontend to restore chat history UI.
3. Wire up Native Tool Calling explicitly in the Groq/Gemini system prompt so voice commands can actually execute the python tools.

## 7. What should be deleted?
- Execute `CLEANUP_PLAN.md`: Delete Kokoro, Deepgram SDK, ElevenLabs SDK, and experimental `.py` tests to drastically lower the Docker/Python footprint.

## 8. What should become the permanent architecture?

**RECOMMENDATION: OPTION A — Cloud-First Pipelined Architecture (Current Model)**

### Evidence / Defense:
1. **Latency**: Groq STT + Gemini TTS is achieving < 1.5s total turnaround time.
2. **Maintenance**: Maintaining local models (Kokoro, Whisper) requires complex ONNX runtime dependencies, immense VRAM/RAM overhead, and platform-specific compilation constraints, breaking the "portable web app" philosophy of Nexus.
3. **Quality**: Gemini TTS provides emotional inflection that Piper/Kokoro struggle to match without heavy prompt engineering.

We must embrace the `Web Audio API <-> WebSocket <-> Groq STT <-> Groq LLM <-> Gemini TTS` pipeline as the **Golden Path** and delete all fallback/experimental code that dilutes it.
