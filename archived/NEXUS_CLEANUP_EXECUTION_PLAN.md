# Nexus Cleanup Execution Plan

Based on the audit of the Nexus codebase, this plan categorizes all major components into actionable buckets to eliminate technical debt, monolithic files, and abandoned experiments.

## 🗑️ DELETE (Immediate Removal)
- **Dead TTS Providers**: `kokoro` implementations, `elevenlabs` implementations.
- **Dead STT Providers**: Local `faster-whisper` fallback scripts, `deepgram` integrations.
- **Abandoned Voice Experiments**: `test_native_audio.py`, `generate_proof.py`, `test_gemini*.py`.
- **Bloated Dependencies**: Any direct script wrapping `vision-agents` without the main WebSocket loop.
- **Duplicate Routes**: Unused or deprecated REST endpoints in `frontend/src/app/api` that duplicate WebSocket functionality.
- **Duplicate UI Hooks**: Deprecated React hooks trying to manage MediaRecorder manually (if superseded by `useNexusVoice.ts`).

## 📦 ARCHIVE (Save for Reference Only)
- **Experimental Branches**: `docs/GEMINI_LIVE_LAB.md`, `docs/NATIVE_AUDIO_FEASIBILITY.md`.
- Move these into an `archive_experiments/` folder completely outside the production `src/` and `voice_agent/` directories.

## 🛠️ REWRITE (Critical Refactoring)
- **The God Class (`ws_main.py`)**: 
  - *Current*: Handles VAD, STT, LLM, TTS, WebSocket, and Session State in >1000 lines.
  - *Target*: Split into `orchestrator.py` (state machine), `vad_service.py` (audio chunking), and `session_manager.py` (WS connections).
- **Audio Processing (`useNexusVoice.ts`)**:
  - *Current*: Mixes React state with raw ArrayBuffer decoding.
  - *Target*: Extract raw audio processing into a pure utility file `lib/audioDecoder.ts`.
- **Tool Registry**:
  - *Current*: Ad-hoc Python functions in `tools/`.
  - *Target*: Rewrite to adhere to Model Context Protocol (MCP) standards.

## ✅ KEEP (The Core)
- **Frontend App Shell**: The Next.js Next 15 router architecture (`frontend/src/app`).
- **Core WebSocket Transport**: The pure `ws://` implementation (once stripped of logic).
- **Groq/Gemini Cloud Pipeline**: The primary high-speed STT/TTS routing logic (`tts_gemini.py`, `tts.py`).
