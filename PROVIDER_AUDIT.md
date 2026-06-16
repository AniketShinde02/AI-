# Provider Audit

| Provider | Status | Role | Notes |
|----------|--------|------|-------|
| **Gemini TTS** | **Active (Primary)** | Text-to-Speech | Configured in `tts_gemini.py`. Uses Gemini Flash 2.5 for text-to-speech generation. |
| **Edge TTS** | **Active (Fallback)**| Text-to-Speech | Configured in `tts_edge.py`. Used if Gemini TTS fails. |
| **Groq (Whisper)** | **Active (Primary)** | Speech-to-Text | Used in `ws_main.py` to transcribe audio chunks instantly. |
| **Groq (Llama3/Gemini)**| **Active (Primary)** | Language Model | Used in `ws_main.py` for standard text generation (via Groq's OpenAI compatible endpoint). |
| **Kokoro** | **Dead Code** | Text-to-Speech | Removed from active routing (`tts.py`), remnants exist in scratch tests. Safe to remove. |
| **Piper** | **Abandoned** | Text-to-Speech | Local TTS engine. Found unmaintained/abandoned in older architectural references. Safe to remove. |
| **Gemini Live** | **Experimental** | E2E Voice | Documented in `docs/GEMINI_LIVE_LAB.md`. Multimodal end-to-end capabilities not currently wired into Nexus WebSocket. |
| **Cartesia** | **Not Used** | Text-to-Speech | No code references found in backend. |

### Summary
The current system successfully implements a pipelined approach (Groq STT -> Groq LLM -> Gemini TTS). Local/Native TTS approaches (Kokoro/Piper) have been abandoned in favor of fast cloud APIs.
