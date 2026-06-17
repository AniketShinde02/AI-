# Voice System Cleanup Plan

The Voice system has accumulated severe technical debt due to multiple pivoted architectures. Here is the strict execution plan.

## 🗑️ DELETE (Dead Weight)
- `backend/voice_agent/providers/tts_kokoro.py` (if it exists)
- `backend/voice_agent/test_native_audio.py`
- `backend/voice_agent/generate_proof.py`
- `backend/test_gemini*.py`
- `requirements_local.txt` (Drop local fallback paradigms)
- Remove `vision-agents` and its plugins from `requirements.txt`. They are bloating memory by ~1.5GB.
- Remove `elevenlabs` and `deepgram-sdk` from `requirements.txt`.

## 📦 ARCHIVE (Valuable References)
- `docs/NATIVE_AUDIO_FEASIBILITY.md`
- `docs/GEMINI_LIVE_LAB.md`
- Move all local TTS model experiment code into an `experimental_archive/` folder.

## ✅ KEEP (Core Architecture)
- `ws_main.py` (The main WebSocket event loop)
- `providers/tts.py` (The abstract TTS interface)
- `providers/tts_gemini.py` (The cloud TTS implementation)
- `frontend/src/hooks/useNexusVoice.ts`
- `frontend/public/worklets/voice-processor.js`

## 🛠️ REWRITE (Needs Refactoring)
- **`ws_main.py`**: It is currently over 1,000 lines long and handles VAD, STT, LLM streaming, TTS queueing, and WebSocket health in one massive class. 
  - *Action*: Split `ws_main.py` into: `orchestrator.py`, `vad_service.py`, `audio_buffer.py`.
- **`useNexusVoice.ts`**: Contains deep audio decoding math alongside UI state logic.
  - *Action*: Move `AudioContext` and `Base64 -> PCM` decoding into a dedicated `/lib/audio.ts` utility file.
