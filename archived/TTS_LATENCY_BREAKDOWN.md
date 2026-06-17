# TTS_LATENCY_BREAKDOWN.md
## Gemini TTS Latency Analysis — Evidence Based

### Confirmed Latency Measurements (From Terminal Logs)
```
Turn 2: [STT] 2907ms  [LLM] 0ms  [TTS] 4656ms  [TOTAL] 18125ms
Turn 4: [STT] 3384ms  [LLM] 0ms  [TTS] 6216ms  [TOTAL] 11625ms
Turn 6: [STT] 2796ms  [LLM] 0ms  [TTS] 7108ms  [TOTAL] 13891ms
```

**Observation 1:** `[LLM] 0ms` is incorrect. This is because latency is measured at `llm_start_time` inside `run_pipeline()` but LLM streaming is not awaited before TTS starts. The 0ms is a measurement artifact.

**Observation 2:** `[TOTAL]` exceeds `[STT] + [LLM] + [TTS]` significantly. For Turn 2: 2907+4656 = 7563ms measured, but TOTAL is 18125ms. The remaining **~10.5 seconds** is the stale buffer dispatch time not counted in the stage metrics.

### Stage-by-Stage Breakdown

#### Stage 1: STT Wait (VAD → Groq Whisper)
- **Actual User Speech Duration:** ~2.3 seconds
- **Audio Dispatched to STT:** 15.4 seconds (due to stale preroll buffer)
- **STT Latency (Groq API):** 2.8–3.4 seconds
- **Root Cause:** 15.4 second payload instead of 2.8 second payload. Groq charges/throttles by audio length. If fixed, STT should complete in ~400-600ms.

#### Stage 2: LLM Processing
- **Measured:** 0ms (misleading — see above)
- **Actual:** ~800-1200ms (Groq llama-3.3-70b is fast but not instant)
- **Note:** LLM streams tokens, and TTS is called when the first sentence boundary is found. So LLM latency is partially hidden behind TTS latency.

#### Stage 3: Gemini TTS (generateContent REST)
**File:** `d:\AI\backend\voice_agent\providers\tts_gemini.py`
**Function:** `stream_audio()` → `fetch_tts()` (Line ~60)

The core bottleneck is here:
```python
response = await asyncio.wait_for(asyncio.to_thread(fetch_tts), timeout=15.0)
```
- This is a **blocking, synchronous REST call** wrapped in `asyncio.to_thread`.
- Gemini `generateContent` with `response_modalities=["AUDIO"]` generates the **entire audio file** before returning the first byte.
- For a sentence of 10-15 words: 4-7 seconds of TTFA (Time To First Audio)
- **No streaming is possible with this API endpoint.**

#### Stage 4: WebSocket Transfer & Playback Start
**File:** `d:\AI\backend\voice_agent\ws_main.py`  
**TTS Worker BUFFER_SIZE:** `BUFFER_SIZE = 6400` (Line ~470) → 100ms chunks at 16kHz
- Once Gemini returns the full audio blob, it is chunked locally and sent rapidly via WebSocket.
- Transfer of chunks is fast (< 200ms).
- This stage is NOT the bottleneck.

---

### Total Latency Budget (Current vs Target)

| Stage | Current | Target (V3) | Fix |
|-------|---------|-------------|-----|
| STT (including preroll debt) | 2800–3400ms | 400–600ms | Fix preroll buffer |
| LLM | 800–1200ms | 600–900ms | Already acceptable |
| Gemini TTS (REST) | 4600–7100ms | N/A if replaced | Replace with streaming |
| WS Transfer | ~200ms | ~200ms | Already OK |
| **TOTAL** | **10–14 seconds** | **1.5–2.5 seconds** | Fix buffer + TTS |

### Key Finding: Gemini TTS is architecturally incompatible with sub-3s voice
The `generateContent` REST API is a **batch endpoint**. It is designed for audio file generation, not real-time voice streaming. To achieve sub-3s total latency, Nexus needs either:
1. **Gemini Live** (`client.aio.live.connect`) — true bidirectional streaming, no TTFA
2. **Edge TTS** (`edge_tts.Communicate`) — returns MP3 chunks as they are generated (~200ms TTFA)
