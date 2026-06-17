# VOICE_V3_ARCHITECTURE.md
## Nexus Voice V3 — Sub-3 Second Target Architecture

### Current Bottleneck Summary
| Stage | Current | Root Cause |
|-------|---------|------------|
| Preroll buffer | 12.8s stale audio | `maxlen=50` × 8192 bytes |
| STT dispatch | 2.8–3.4s (15.4s payload) | Stale preroll inflates Groq API time |
| Gemini TTS | 4.6–7.1s | REST batch endpoint, no streaming |
| **Total** | **10–18 seconds** | |

### Target
```
User speaks 2s → Response audio starts: under 3 seconds total
```

---

### V3 Architecture Design (Dual-Mode)

#### Mode A — Gemini Live (Primary, Sub-1s)
```
Browser Mic (16kHz PCM) 
  → WebSocket → Python Gateway
  → Gemini Live aio.live.connect (gemini-2.5-flash-native-audio-preview)
  → Raw audio chunks stream back immediately
  → WebSocket → Browser AudioContext
```
- **TTFA:** 300–800ms
- **No VAD needed** (Gemini handles turn-detection natively)
- **No separate STT** (Gemini understands audio natively)
- **No separate TTS** (Gemini returns audio directly)
- **Rate limit risk:** Gemini free tier (limited RPM)
- **Existing code:** `experimental/gemini_live_voice.py` — needs production hardening

#### Mode B — Groq STT + LLM + Edge TTS (Fallback, Sub-3s)
```
Browser Mic (16kHz PCM)
  → WebSocket → Python Gateway
  → VAD (Silero) → Speech end detected
  → Groq Whisper (FIXED: 2.5s payload instead of 15.4s) → Text
  → SpeechCleaner (Groq llama-3.1-8b-instant) → Normalized Text
  → Groq llama-3.3-70b (streaming) → Sentence tokens
  → Edge TTS (en-IN-PrabhatNeural/NeerjaNeural) → MP3 stream → PCM
  → WebSocket → Browser AudioContext
```
- **TTFA:** 1.5–2.5 seconds (after preroll fix and Edge TTS)
- **Requires fixes:** preroll buffer, speech cleaner model, replace Gemini REST TTS with Edge TTS

---

### Changes Required Per Mode

#### Fixes Needed for Mode B (Current Pipeline Repaired)
1. **Preroll buffer** `ws_main.py`: Change `maxlen=50` to `maxlen=8`; add `clear()` after prepending
2. **SpeechCleaner** `speech_cleaner.py` Line 10: Change model from `llama3-8b-8192` to `llama-3.1-8b-instant`
3. **Gemini TTS → Edge TTS swap**: Stop calling `tts_gemini.py` for real-time voice; use `tts_edge.py` as primary with Indian accent enforcement
4. **Dead imports in `tts.py`**: Remove `getstream`, `vision_agents`, `kokoro_onnx` imports

#### Upgrades Needed for Mode A (Gemini Live)
1. **Production-harden** `experimental/gemini_live_voice.py`:
   - Add automatic reconnection (retry loop with exponential backoff)
   - Add interruption: cancel outgoing audio when new input detected
   - Add conversation history injection at session start
   - Add tool_call interception and routing
2. **Wire into `ws_main.py`** as primary route, with Mode B as fallback when Live session fails

---

### State Machine (V3)
```
States: IDLE → LISTENING → THINKING → SPEAKING → IDLE

Mode A (Gemini Live): No discrete states. Audio flows continuously.
Mode B (Current Pipeline): Existing state machine, repaired.

UI Shows:
IDLE:      "Ready"
LISTENING: "Listening..."
THINKING:  "Thinking..."
SPEAKING:  "Speaking..."
ERROR:     "Retrying..."  ← Never show raw errors to user
```

---

### Latency Budget (V3 Targets)
| Stage | Mode A (Gemini Live) | Mode B (Repaired Pipeline) |
|-------|---------------------|--------------------------|
| VAD / Input | 0ms (streaming) | 400ms (max with fixed preroll) |
| STT | 0ms (built-in) | 400-600ms (2.5s payload to Groq) |
| Speech Cleanup | 0ms (built-in) | 80-120ms (llama-3.1-8b-instant) |
| LLM | ~500ms built-in | 600-900ms (Groq streaming) |
| TTS | ~200ms built-in | 200ms TTFA (Edge TTS streaming) |
| **Total TTFA** | **~700ms** | **~1.7-2.1 seconds** |
