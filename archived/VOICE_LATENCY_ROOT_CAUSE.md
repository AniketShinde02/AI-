# Voice Latency Forensic & Root Cause Analysis

This document provides a strictly evidence-based analysis of the voice pipeline latency in Nexus, adhering to the "PHASE 4.5 — VOICE LATENCY FORENSIC" mandate.

## 1. The 15.4s Audio Dispatch Mystery (Stale Buffer Accumulation)
**Symptom**: User speaks for ~2 seconds, but VAD dispatches 15.4 seconds of audio to STT.
**Root Cause**: The `vad_preroll_buffer` is accumulating indefinitely and prepending stale audio to every new utterance.
**Exact Location**: `d:\AI\backend\voice_agent\ws_main.py`
**Line Numbers**: 
- Initialization: `self.vad_preroll_buffer: Deque[bytes] = deque(maxlen=50)` (Line ~200)
- The Flaw: The `maxlen=50` limits the buffer to 50 *chunks*. However, if the frontend sends chunks of 8192 bytes, 50 chunks = 409,600 bytes. At 16kHz (32,000 bytes/sec), this equals **12.8 seconds** of raw, un-cleared audio context that gets prepended to *every single* speech dispatch.
- Execution: `preroll_context = b"".join(self.vad_preroll_buffer)` (Line ~330)

## 2. Speech Cleaner Failure
**Symptom**: The Speech Cleaner pipeline silently passes through messy text.
**Root Cause**: Groq has officially decommissioned the `llama3-8b-8192` model.
**Evidence**: Terminal logs show a hard HTTP 400 error:
`{'error': {'message': 'The model llama3-8b-8192 has been decommissioned...`
**Exact Location**: `d:\AI\backend\voice_agent\speech_cleaner.py`
**Line Number**: Line 10 (`self.model = "llama3-8b-8192"`)

## 3. Model References Across Codebase
A deep search reveals the following hardcoded models:
- **Speech Cleaner**: `llama3-8b-8192` (Decommissioned, fails instantly) in `speech_cleaner.py`.
- **Primary LLM**: `llama-3.3-70b-versatile` in `providers/llm.py` and `main.py`.
- **RAG Oracle**: `llama-3.1-8b-instant` in `core/rag_oracle.py`.
- **Groq STT**: `whisper-large-v3-turbo` in `providers/stt.py` and `whisper-large-v3` directly in `ws_main.py`.

## 4. TTS Engine Analysis
### Gemini TTS (Mode 1)
- **Exact File**: `providers/tts_gemini.py`
- **Voice Mapping**: Maps `nexus_male` to `Puck`, `sarah` to `Aoede`, `professional_male` to `Fenrir`, and `casual_female` to `Kore`.
- **Latency Issue**: Gemini TTS uses `generateContent` with `response_modalities=["AUDIO"]`. It generates the *entire* audio file before returning the first byte. It cannot stream byte-by-byte like true streaming TTS engines, resulting in 4-8 second TTFA (Time To First Audio) spikes.

### Edge TTS (Fallback)
- **Exact File**: `providers/tts_edge.py`
- **Voice Mapping**: 
  - Male (Indian English): `en-IN-PrabhatNeural`
  - Female (Indian English): `en-IN-NeerjaNeural`
  - Male (US English): `en-US-GuyNeural`
  - Female (US English): `en-US-JennyNeural`
- **Limitations**: Edge TTS provides extremely high-quality Indian accents but relies on undocumented Microsoft endpoints, making it slightly slower to connect than dedicated APIs like Cartesia or ElevenLabs.

## 5. Architectural Comparison
- **IRIS**: Uses deep desktop integration and local memory, but its Electron monolith makes voice routing heavy.
- **Hermes**: The gold standard. Uses a highly decoupled Gateway (MCP) with `batch_runner.py` for parallel execution. Audio chunks are handled flawlessly because Hermes maintains strict buffer lifetimes (`hermes_state.py`).
- **Stonic**: Over-simplified. Just wraps API endpoints in Electron.
- **Current Nexus**: Suffers from the "God Class" anti-pattern in `ws_main.py`. Because VAD, WebSocket, Buffers, and LLM logic share the exact same class state, a misconfigured `maxlen` on a single deque accidentally cascades into a 15-second latency delay for the Groq Whisper STT API.

## Recommended Fix Strategy
1. **Fix the Preroll Buffer**: Reduce `vad_preroll_buffer` `maxlen` dynamically based on chunk size (e.g., target exactly 0.5 seconds of context), and clear it upon successful TTS output.
2. **Upgrade the Denoising Model**: Change `llama3-8b-8192` to `llama-3.1-8b-instant` in `speech_cleaner.py` to restore the sentence cleanup pipeline.
3. **Decouple audio processing**: Move VAD chunking out of the WebSocket connection class into a dedicated pure Python buffer manager.
