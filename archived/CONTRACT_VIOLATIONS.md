# Contract Violations Audit

This document tracks where data objects cross boundaries and where their schemas have historically mismatched or currently mismatch.

## 1. TTS Provider Router Interface (FIXED)

**Boundary:** `tts_router.py` -> `ws_main.py` (TTS Worker)

**Expected Object:** `AsyncIterator[PcmData]` (Yields chunks of audio).
**Actual Object:** Yields `dict` (metadata containing provider info), THEN yields `PcmData`.
**Violation:** `ws_main.py` iterated blindly and called `.samples.tobytes()` on the first item, resulting in the crash: `'dict' object has no attribute 'samples'`.
**Status:** **Fixed**. `ws_main.py` now uses an `isinstance(pcm_data, dict)` check to filter metadata.

## 2. Frontend to Backend Audio Transmission (VALID)

**Boundary:** `useNexusVoice.ts` -> `ws_main.py`

**Expected Object:** Raw bytes representing PCM audio at 16kHz.
**Actual Object:** Frontend buffers `Float32Array`, converts to `Int16Array`, and sends `ArrayBuffer` directly over WebSocket.
**Status:** **Valid**. VAD and STT expect 16kHz Int16 bytes.

## 3. Backend to Frontend Audio Transmission (VALID)

**Boundary:** `ws_main.py` (TTS Worker) -> `useNexusVoice.ts`

**Expected Object:** JSON payload containing Base64 encoded audio string.
**Actual Object:** `{"type": "audio_chunk", "data": "base64...", "meta": {...}}`.
**Status:** **Valid**. Frontend decodes base64 back into `Float32Array` for the `AudioContext`.

## 4. LLM Response Streaming (VALID)

**Boundary:** Groq API -> `ws_main.py` -> `useNexusVoice.ts`

**Expected Object:** Server-Sent Events / Chunked text.
**Actual Object:** Evaluates chunks, filters out thinking `<think>` tags, sends sanitized `agent_message` JSON payloads.
**Status:** **Valid**.

## 5. Tool Call Execution (EXPERIMENTAL)

**Boundary:** LLM -> `ws_main.py` -> `tools/`

**Expected Object:** Native tool calling JSON schema.
**Actual Object:** The system contains `third_party_tools.py`, but it is currently decoupled from the main voice pipeline routing loop.
**Violation:** The voice loop does not reliably pass tool schemas to Groq/Gemini in real-time, relying entirely on pure text generation.
**Status:** **Needs Wiring**.
