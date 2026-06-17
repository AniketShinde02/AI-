# Dependency Audit

## Python Backend Dependencies (`backend/requirements.txt` & `requirements_local.txt`)

| Package | Status | Usage / Notes |
|---------|--------|---------------|
| `vision-agents` | Heavy / Unused | Experimental plugin, unused in core voice loop. Bloats startup. |
| `vision-agents-plugins-*` | Heavy / Unused | Deepgram/ElevenLabs plugins unused since we moved to Gemini/Edge. |
| `aiortc` | Unused | WebRTC is not currently used; we use pure WebSockets for audio streaming. |
| `getstream` / `stream-chat` | Experimental | Stream's SDK is heavy; currently audio streaming bypasses Stream's infrastructure directly via WebSocket. |
| `groq` | Required | Active dependency for STT (Whisper) and LLM text generation. |
| `deepgram-sdk` | Abandoned | Deepgram was previously used for STT but replaced by Groq. |
| `elevenlabs` | Abandoned | ElevenLabs TTS is currently disabled. |
| `redis` | Active | Used for some rate limiting/caching or planned pub/sub. |
| `firebase-admin` | Active | Used for backend auth verification. |
| `faster-whisper` | Abandoned | Local STT fallback is dead code. We rely purely on cloud Groq Whisper. |
| `kokoro-onnx` | Abandoned | Local TTS fallback is dead code. Heavy (~2GB+ models). |
| `psutil` | Required | Currently used to stream backend telemetry to frontend. |

### Summary
The backend is carrying significant technical debt via `vision-agents`, WebRTC, and abandoned TTS/STT SDKs (Deepgram, ElevenLabs, Kokoro, Faster-Whisper).

**Startup Cost:** High due to ONNX/PyTorch and Vision Agents loading.
**Memory Cost:** Moderate. Removing Kokoro/Faster-Whisper and Vision Agents would reduce idle memory significantly.
