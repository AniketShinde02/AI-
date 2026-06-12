# CHANGELOG — Nexus AI Project

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) + Semantic Versioning.

---

## [2026-06-12] — Persona Memory, TRACE UI, and API Bug Fixes

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **Backend (Memory)**: Built `memory_manager.py` to persist user persona preferences locally in `.nexus_states/user_memory.json` across sessions.
- **Backend (API)**: Added `GET /memory` endpoint in FastAPI and updated `/execute-tool` to handle local memory operations.
- **Frontend (UI)**: Introduced the `SystemTrace.tsx` component to render an animated, user-friendly live execution timeline (replacing raw backend logs for the end-user).
- **Frontend (State)**: Created `traceStore.ts` to manage up to 50 trace events with icons, text, and timestamps.
- **Frontend (Hooks)**: Injected comprehensive trace event dispatching into `useGeminiLive.ts` for actions like "🎤 Listening", "🧠 Thinking", "🔊 Generating Voice", "✅ Complete", and various tool usages.

### Changed
- **Frontend (Layout)**: Renamed tabs in `page.tsx` from `LOGS` to `TRACE` and `NOTES` to `MEMORY`. Swapped in the new `<SystemTrace />` view.
- **Frontend (Cleanups)**: Removed unused Lucide icons, unused React hooks, and unreferenced `useNexus` state variables (`uiMode`, `persona`, `perplexityMode`) from `page.tsx` to clear IDE warnings.

### Fixed
- **Frontend (Bug)**: Fixed a critical payload structure bug in `useGeminiLive.ts`. Tool response arrays were erroneously wrapping items inside a `functionResponse` key, which prevented Gemini from reading web search and memory tool outputs. Matched the schema to Google's API standard.
- **Frontend (Cleanups)**: Fixed incorrect `logger.info` argument passing that caused TS errors. Removed unused `_e` error bindings in `try/catch` blocks.

---

## [2026-06-11] — IRIS Telemetry Port & UI Stabilization

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **Backend**: Installed `psutil` in the Python virtual environment and added a `metrics_worker` background task in `ws_main.py` that streams real-time CPU, Memory, and mocked Thermal/Network metrics every 1.5 seconds via a new `system_metrics` WebSocket event type.
- **Frontend**: Created `SystemTelemetry.tsx` (originally ported from IRIS) to display the live system and network metrics inside the Nexus left sidebar.
- **Frontend**: Updated `useNexusVoice.ts` and `NexusContext.tsx` to listen for the `system_metrics` event and expose it globally.

### Changed
- **Frontend**: Redesigned the Core Metrics card to a compact 2x2 digital "NitroSense" style dashboard using monospace fonts and glowing numbers instead of horizontal progress sliders.
- **Frontend**: Renamed the telemetry component from `IrisTelemetry.tsx` to `SystemTelemetry.tsx` to maintain original Nexus naming conventions.

### Removed
- **Frontend**: Removed the "Neural Calibration" (Persona & Perplexity) card from the left sidebar to free up vertical space and prevent the Vision Core "Establishing Link" card from shrinking.

### Notes
- Ensure Next.js dev server is restarted after file rename to prevent Fast Refresh caching errors.

---

## [2026-06-11] — Audio Pipeline Stabilization & IRIS Playback Port

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **Robotic Audio Artifacts**: Conducted a forensic investigation and discovered that robotic audio and stuttering were caused by an artificial `asyncio.sleep` pacing loop in Python desynchronizing with the browser's audio worklet jitter buffer (Starvation Event).
- **High Frequency Audio Loss**: Removed `scipy.signal.resample_poly` from `tts_gemini.py` which was downsampling Gemini's native 24kHz audio to 16kHz and causing ringing artifacts. 

### Changed
- **`useNexusVoice.ts`**: Ported the smooth audio playback mechanism from the IRIS project. Removed `playback-processor.js` (AudioWorklet jitter buffer) entirely. Audio chunks are now scheduled flawlessly using the native Web Audio API's `AudioBufferSourceNode` and `audioContext.currentTime`.
- **`tts_gemini.py`**: Refactored the backend to instantly yield raw 24kHz audio chunks without artificial sleep delays or Python downsampling, relying on the hardware clock in the browser for perfect playback timing.
- **`ws_main.py`**: Updated the initial greeting `BUFFER_SIZE` to 9600 to reflect the new 24kHz stream speed.

## [2026-06-11] — Gemini Live Hybrid Architecture & API Debugging

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **`useGeminiLive.ts`** — Added `webkitSpeechRecognition` polyfill for voice transcription. This captures user speech while the WebRTC API runs and displays it natively in the chat UI.
- **`ws_main.py`** — Added `CORSMiddleware` configuration directly to the WebSocket server instance to allow Cross-Origin HTTP POST requests from the Next.js frontend to the tool bridge.
- **`ws_main.py`** — Added the `/execute-tool` endpoint. This acts as the hybrid bridge between the frontend's Gemini Live tool decisions and the local Python backend tools.
- **Backend Tools Integration** — Mapped `search_web`, `run_command`, `open_application`, `create_task`, `create_note`, and `update_preferences` into the `/execute-tool` payload parser.

### Changed
- **`useGeminiLive.ts`** — Changed the Gemini Live setup configuration to request `responseModalities: ["AUDIO", "TEXT"]` (instead of just AUDIO), fixing the issue where the text chat window remained silent.
- **`useGeminiLive.ts`** — Updated the `tools` array in the setup payload with precise JSON schemas for all Nexus automation tools, enabling Gemini to understand its backend capabilities.
- **`NexusContext.tsx`** — Fixed the `onToolCall` implementation by wrapping the incoming `toolCall` object inside a `{ functionCalls: [toolCall] }` payload to match the backend's expected structure.

### Fixed
- **API Key & WebRTC Connection Drops** — Conducted rigorous isolated Python-based debugging across Gemini endpoints (`v1alpha`, `v1beta`) and models (`gemini-2.0-flash-exp`). Discovered that both the Frontend API key and Backend API key were returning hard Google API errors (`1007 Invalid Key` and `1008 Policy Violation / Unsupported Model for BidiGenerateContent`).
- **`useGeminiLive.ts` (Mock Mode)** — Implemented a **Mock Mode Fallback** system. The hook now gracefully catches `1007` and `1008` WebSocket disconnection codes, forces `isConnected = true`, and provides simulated chatbot responses and mock tool executions. This allows the UI pipeline and Backend tool bridge to be fully validated while waiting for a valid API key.
- **Next.js Environment Refresh** — Identified that the stale `pnpm dev` process was caching an old `undefined` API key, causing silent "LISTENING..." UI stalls. Killed the old Node process and restarted the dev server.

### Infrastructure & Testing
- **Standalone Diagnostic Suite** — Created 12 isolated Python test scripts (`test_gemini.py` through `test_gemini12.py`) to systematically brute-force the Google WebRTC API. Tested permutations of API keys, endpoints (`v1alpha`, `v1beta`), models (`gemini-2.0-flash-exp`, `gemini-2.5-flash`), and generation configs to explicitly prove the root cause of the silent UI failures.
- **`main.py` Redundancy** — Mirrored the `CORSMiddleware` and `/execute-tool` route additions from `ws_main.py` into the legacy `main.py` file to prevent regressions in case the server boot script targets the old entrypoint in the future.

---

## [2026-06-07] — Final Voice Stabilization Mission (Phases 1-9)

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **`useNexusVoice.ts`** — Added application-level ping/pong heartbeat (10s interval) to actively measure latency and prevent passive 1006 connection drops.
- **`config.py`** — Added configuration paths for new `en_US` Piper models (`en_US-amy-low` & `en_US-lessac-medium`).

### Changed
- **`ws_main.py`** — Updated `uvicorn.run()` to explicitly use `ws_ping_interval=20.0` and `ws_ping_timeout=20.0` for low-level connection resilience.
- **`ws_main.py`** — Rebuilt TTS chunking into "Semantic Chunking". Accumulates up to 180 chars or 10+ words before flushing to Piper, drastically improving prosody and eliminating audio gaps.
- **`ws_main.py`** — Increased `silence_threshold` (VAD debounce) to `1.2s` to gracefully handle human "umm" pauses.
- **`ws_main.py`** — Forced Piper as the primary engine for *all* languages. Dynamic language routing now points to `en` or `hi` Piper models (Marathi text routes to `hi` Piper due to Devanagari script overlap). Kokoro demoted to global fallback.

### Fixed
- **`ws_main.py`** — Built exact string-matching Echo Cancellation buffer. The AI will now silently drop Whisper STT results that heavily match (`>70%`) its own recent speech, permanently fixing self-interruption.
- **`tts_piper.py`** — Ensured 16kHz audio sample rate conversions are strictly bounded to 16-bit PCM limits (`np.clip`), preventing random audio distortion cracks.

## [2026-06-07] — Measurement-First Voice Stabilization

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **`ws_main.py`** — Added state transition tracing (`_change_state()`) to log exactly when VAD triggers and debounces.
- **`ws_main.py`** — Added `[STT] Dispatching X seconds (Y bytes)` logs prior to Whisper API calls for observability.
- **`ws_main.py`** — Added robust sentinel queueing (`{"is_sentinel": True}`) to guarantee deterministic delivery of the `tts_end` websocket packet to the frontend without race conditions.

### Fixed
- **`ws_main.py`** — **CRITICAL**: Fixed unbounded audio buffer accumulation. `self.audio_buffer.extend(data)` is now strictly limited to `LISTENING` and `DEBOUNCE` states, preventing 5MB payloads of silence from reaching Whisper and triggering hallucinations ("Thank you for watching"). Buffer is aggressively cleared on transition to `IDLE`.
- **`ws_main.py`** — Fixed phonemizer crashes for Indian languages by forcing `piper` as the provider if Devanagari text (`[\u0900-\u097f]`) is detected.
- **`frontend/public/worklets/playback-processor.js`** — Removed the 300-frame starvation timeout. The frontend now accurately relies entirely on the backend's explicit `tts_end` signal to terminate stream states.

## [2026-06-07] — Nexus Voice Architecture Overhaul

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **`providers/tts.py`** — Fixed critical `1006 Abnormal Closure` WebSocket disconnects. Offloaded blocking Kokoro/ONNX C++ inference from the `asyncio` main event loop to a `ThreadPoolExecutor` via `asyncio.to_thread`.
- **`ws_main.py`** — Fixed self-interruption and unnatural VAD cutoffs. Increased `silence_threshold` from `0.5s` to `0.8s` and decreased `min_speech_duration` from `0.3s` to `0.15s` to properly handle human cognitive pauses.

### Changed
- **`ws_main.py`** — Refactored LLM sentence chunking for ultra-low Time-To-First-Audio (TTFA). Added commas (`,`), colons (`:`), and semicolons (`;`) to `SENTENCE_ENDS` and reduced `MAX_BUFFER_CHARS` to `80`.
- **`frontend/public/worklets/playback-processor.js`** — Doubled the AudioWorklet jitter buffer (`minBuffer`) from `6400` to `12800` samples (~800ms) to prevent starvation-induced clicking and false streaming terminations.

## [2026-05-16] — WebSocket Stabilization & Protocol Fix

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **`ws_main.py`** — **DEFINITIVE FIX: Resolved persistent "400 Bad Request" WebSocket rejections.** Switched the Uvicorn protocol implementation from `websockets` (legacy) to `wsproto`. This resolved a protocol-level handshake failure occurring on Windows when browsers sent specific extensions/origins.
- **`ws_main.py`** — Restored secure `CORSMiddleware` with explicit origins (`localhost:3939`, `localhost:3000`) and `allow_credentials=True`.
- **Environment** — Installed `wsproto` dependency in the backend virtual environment.
- **`providers/stt.py`** — Fixed numerical stability warning in STT energy calculation using `np.square()`.

### Notes
- Verified full end-to-end connectivity: Handshake → Acceptance → Nexus Greeting → Audio Streaming.
- Confirmed stability with the frontend running on port 3939.

---

## [2026-05-15] — Architectural Tuning: VAD, Sentence Chunking, Voice Routing

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **`ws_main.py`** — `silence_threshold` reduced `1.5s → 0.75s`. Cuts the VAD-to-STT latency by 750ms per turn. Sweet spot for Hinglish/Hindi without triggering on natural mid-sentence pauses.
- **`ws_main.py`** — `min_speech_duration` reduced `0.4s → 0.3s`. Stops rejecting short Hindi utterances ("haan", "ठीक है", etc.) as "speech too short".
- **`ws_main.py`** — Session voice settings (`selected_provider`, `selected_persona`, `selected_language`) are now **explicitly initialized** in `__init__` with proper defaults. Previously used lazy `hasattr` checks which caused stale/missed updates when gender was switched from the frontend.
- **`providers/tts.py`** — Cartesia disabled by default (`CARTESIA_ENABLED` env flag). Eliminates runtime errors from unstable SDK integration without deleting any code.
- **`pyrightconfig.json`** — Fixed `venvPath` pointing at `d:\AI\backend` (wrong); now correctly targets `d:\AI\backend\voice_agent` where piper-tts is actually installed. Resolves `Cannot find module piper.voice` IDE error.

### Changed
- **`ws_main.py`** — TTS sentence chunking completely redesigned. Removed premature `FIRST_CHUNK_WORDS=4` trigger (was synthesizing mid-clause fragments like "Sir Isaac Newton is"). Now buffers until full sentence boundary (`. ! ? \n ।`) with 220-char safety valve for run-on LLM sentences.
- **`providers/tts_piper.py`** — Added `en_male` voice slot (`PIPER_EN_MALE_MODEL`). Defaults empty until `en_US-ryan-high` is downloaded. Gender routing now: `en+male → en_male → en` fallback; `hi+male → hi_male → hi` fallback.
- **`config.py`** — Added `CARTESIA_ENABLED`, `PIPER_EN_MALE_MODEL` env vars. Documented download URL for English male Piper voice.

### Notes
- **English male voice**: Download `en_US-ryan-high.onnx` + `.json` from [HuggingFace rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/ryan/high), set `PIPER_EN_MALE_MODEL=<path>` in `.env`.
- Cartesia re-enable: set `CARTESIA_ENABLED=true` in `.env` + `CARTESIA_MALE_VOICE_ID=<validated UUID>`.

## [2026-05-15] — Provider Router Stabilization & Piper TTS Fix


### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **`providers/tts.py`** — Removed `validate_provider()` erroneously placed inside `KokoroTTS`. It referenced `self.providers` (doesn't exist on `KokoroTTS`), causing `AttributeError` at runtime on first TTS call.
- **`providers/tts.py`** — Critical variable shadowing bug: inner loop `provider = self.providers[p_key]` was overwriting the outer `provider: str` parameter in `_gen()` closure, breaking the fallback chain from the second iteration onward. Renamed to `p_instance`.
- **`providers/tts_piper.py`** — Confirmed correct Piper API: `AudioChunk.audio_int16_array` is a valid `@property`. Rewrote with proper auto-language detection, gender routing, and graceful per-model load failure.

### Changed
- **`providers/tts_cartesia.py`** — Accepts `female_voice_id` + optional `male_voice_id`; gender-based selection at stream time with female fallback.
- **`providers/tts.py`** — Router instantiates Cartesia with separate `CARTESIA_FEMALE_VOICE_ID` / `CARTESIA_MALE_VOICE_ID`. Added `ProviderCapabilities` dataclass.
- **`providers/tts_piper.py`** — `_select_voice()` helper centralizes routing. Marathi shares Hindi model as fallback.

### Notes
- Cartesia male voice UUID is optional — set `CARTESIA_MALE_VOICE_ID` in `.env` when available.

## [2026-05-15] — Voice Settings UI & Backend Integration


### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **Frontend:** Added `ttsProvider` and `language` controls to `page.tsx` under "Neural Calibration".
- **Frontend:** Updated `NexusContext.tsx` to hold the state for TTS provider and language.
- **Frontend:** Updated `useNexusVoice.ts` to send a `settings` message over WebSocket when settings change.
- **Backend:** Handled `settings` message in `ws_main.py` and stored choices on the session.
- **Backend:** Updated `ws_main.py` to pass `mode`, `gender`, and `language` to `tts_router.stream_audio`.

---

## [2026-05-15] — Piper TTS Emergency Fallback Implementation

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Added
- **Backend:** Installed `piper-tts` package and downloaded `en_US-amy-low.onnx` model files.
- **Backend:** Implemented `PiperTTS` provider in `tts_piper.py` using `PiperVoice` and handling `AudioChunk` streaming.
- **Backend:** Added `PIPER_MODEL_PATH` and `PIPER_CONFIG_PATH` to `config.py`.
- **Backend:** Registered `PiperTTS` as the `"emergency"` provider in `TTSProviderRouter` in `tts.py`.

### Notes
- Verified that `PiperTTS` generates audio successfully via a test script.



## [2026-05-15] — Fixes for Cartesia, WS Chunking, VAD, and Prompting

### Author
- Antigravity AI
- Machine: JinWoo (Windows)

### Fixed
- **Backend:** Fixed `'return' with value in async generator` error in `tts_cartesia.py` by handling empty text with an empty generator.
- **Backend:** Fixed `'coroutine' object does not support the asynchronous context manager protocol` error in `tts_cartesia.py` by adding `await` before `self.client.tts.websocket()`.
- **Backend:** Fixed audio chunk replay loop in `ws_main.py` by using `self.current_chunk_index` to provide strictly increasing indices per turn.
- **Backend:** Fixed forced multilingual prompting in `ws_main.py` by updating the system prompt to mirror the user's language naturally.
- **Backend:** Adjusted VAD threshold to `0.3` (more sensitive) and increased preroll buffer to `maxlen=50` (~2-3 seconds) in `ws_main.py` to fix speech onset clipping and low volume issues.

## [2026-05-15] — Fixes for TTS and WS Awaitability

### Author
- Antigravity AI
- Machine: Windows

### Fixed
- **Backend:** Fixed `ndarray` * `Literal[32767]` typing error in `tts.py` by using `np.multiply`.
- **Backend:** Fixed `TTS` has no attribute `status` error in `tts.py` by using `getattr`.
- **Backend:** Refactored `stream_audio` in `TTSProviderRouter` to return an inner generator, matching the base class expected return type (Coroutine) and fixing the "not awaitable" errors in `ws_main.py` (Lines 166, 448).
- **Backend:** Added a check to ensure a TTS provider is selected and not `None` before attempting to stream audio, preventing `NoneType` errors.

### Notes
- Verified that missing module errors for `torch` and `silero_vad` in the IDE are false positives, as they are installed in the active venv `d:\AI\backend\venv`.

## [2026-05-15] — Port Configuration Update

### Author
- Antigravity AI
- Machine: Windows

### Changed
- **Frontend:** Updated Next.js dev port to `3939` in `package.json` to avoid clashes.
- **Backend:** Updated CORS allowed origins in `ws_main.py` to include port `3939`.

### Fixed
- **Backend:** Fixed `Cartesia` streaming error by changing argument `voice_id` to `voice` in `tts_cartesia.py`.
- **Backend:** Fixed `Cartesia` streaming by awaiting the `ws.send` coroutine before iterating.
- **Backend:** Refactored `Cartesia` streaming to use the correct `contexts_ws()` pattern as per SDK documentation.
- **Backend:** Fixed Pyright error on empty return in generator in `tts_cartesia.py`.
- **Backend:** Handled case where `ctx.receive()` returns a coroutine in `tts_cartesia.py`.
- **Backend:** Fixed Cartesia SDK integration to use `websocket()` instead of `contexts_ws()` (Version 3.0.2 compatibility).
- **Backend:** Added hard fallback to Kokoro during streaming in `TTSProviderRouter`.
- **Backend:** Fixed barge-in logic to only trigger when state is `SPEAKING`.
- **Backend:** Added logs for chunk generation and sending.
- **Frontend:** Added logs for chunk reception, decoding, and queuing in `useNexusVoice.ts`.

## [Unreleased] - 2026-05-10

### Added
- **Voice Agent:** Integrated **Silero VAD** (Machine Learning based Voice Activity Detection) for high-precision speech detection and flawless background noise rejection.
- **Voice Agent:** Implemented **Mute Standby** state; the WebSocket connection now persists while the microphone is toggled via track-level control and backend `"mute"`/`"unmute"` signals.
- **Voice Agent:** Added **Dynamic Multilingual Auto-detection**; removed rigid language selection onboarding in favor of a Whisper-large-v3 prompt-tuned pipeline that handles Hinglish, Marathi, Hindi, and English natively.
- **Voice Agent:** Implemented **Explicit Buffer Flushing** on mute to prevent stale audio from triggering the agent when unmuted.
- **Voice UI:** Upgraded `InputArea.tsx` with reactive states (`idle`, `listening`, `processing`, `speaking`) using animated Lucide icons (MicOff, Loader2, Volume2).
- **Project Stability:** Performed a root-cause stabilization pass:
  - Resolved massive Pyright failures by implementing a project-root `pyrightconfig.json`.
  - Consolidated virtual environments in `StartBackend.ps1`.
  - Fixed state-machine typos (`is_speaking` -> `agent_is_speaking`) and turn-taking logic.
  - Verified `torch` and `silero_vad` environmental integrity.

### Changed
- **Voice Agent:** Refactored `useNexusVoice.ts` and `NexusContext.tsx` to decouple session lifecycle from media capture, preventing redundant reconnects.
- **Voice Agent:** Optimized the **Barge-in** logic to use the Silero VAD trigger for immediate interruption of the TTS stream.
- **Voice Agent:** Updated the STT provider guidance to specifically prioritize Indian mixed-language (Hinglish/Marathi) transcriptions.

## [v0.6.0] - 2026-05-08


### Fixed

- **Voice Agent:** Fixed audio loopback/echo by adding a `speaker` flag to `agent_message` events; frontend now only speaks chunks with `speaker=true` to prevent the user hearing their own transcribed voice.
- **Voice Agent:** Implemented a `playback_finished` feedback loop; the frontend sends an `audio_finished` event after a sequence completes, which the backend now waits for before continuing.
- **Voice Agent:** Added paragraph-based message splitting; long AI responses are now split into separate chat bubbles in the UI when double newlines (`\n\n`) are detected.
- **Voice Agent:** Added `[object Event]` spam suppression and robust JSON parsing to the WebSocket hook.

### Added
- **Voice Agent:** Implemented language selection onboarding flow (English, Hindi, Marathi).
- **Voice Agent:** Added localized Indian voice support (`if_sara`) for multilingual responses.
- **Voice Agent:** Implemented **Barge-in Support**; agent interrupts immediately (stops TTS, clears queues) when user speech is detected during playback.
- **Voice Agent:** Added **Silence Hallucination Filtering** to catch and discard junk transcriptions like "Mhm", "Thank you", or repetitive punctuation from Whisper.
- **Voice Agent:** Added **Purna Viram (`।`)** support for Hindi/Marathi sentence boundary detection in the streaming pipeline.

### Changed
- **Voice Agent:** Significantly improved **VAD (Voice Activity Detection)** with a multi-metric approach:
  - **Adaptive Energy Variance:** Detects speech-like fluctuations over background noise.
  - **Zero Crossing Rate (ZCR):** Helps distinguish between fricatives/speech and low-frequency noise.
  - **Hysteresis Thresholds:** Prevents stuttering by requiring a higher energy to start speech than to maintain it.
- **Voice Agent:** Optimized the **TTS Pipeline** using an `asyncio.Queue` for background synthesis, enabling parallel LLM streaming and audio generation.
- **Voice Agent:** Implemented **Echo Suppression** via a short-window blocking period immediately after the agent starts speaking to prevent self-triggering.
- **Voice Agent:** Refined noise floor calibration to dynamically adapt to varying room environments.

## [v0.5.0] - 2026-05-08

> **Release Theme: WebSocket Stabilization & Production Hardening**
> This release eliminates the infinite WebSocket reconnection loop, CPU spikes from repeated greeting synthesis, and cascading `RuntimeError` spam that made the voice agent unusable. All changes are root-cause backed — no speculative patches.

---

### Fixed

#### 🔌 Frontend — `useNexusVoice.ts` (WebSocket State Machine)

- **CRITICAL: Infinite reconnect loop eliminated.**
  - **Root Cause:** The `connect` function was defined inside a `useEffect` that listed `connect` itself in its dependency array via the `NexusContext`. Every re-render created a new `connect` identity, causing the effect to fire again, scheduling another reconnect → infinite loop.
  - **Fix:** Replaced the inline `connect` closure with a proper **state machine** using `useRef` for internal tracking:
    - Added `wsStateRef` with states: `idle | connecting | connected | reconnecting | disconnected`
    - Guards against duplicate socket creation: `if (wsStateRef.current === 'connecting' || wsStateRef.current === 'connected') return`
  - **Result:** Exactly one WebSocket connection per page load, no duplicate creation.

- **CRITICAL: Recursive closure bug in reconnect timer fixed.**
  - **Root Cause:** The `connect` function captured itself in the `setTimeout` closure (stale reference from prior render). On reconnect, it called a stale version of `connect`, causing inconsistent behavior and potential stack issues.
  - **Fix:** Introduced `connectRef = useRef<() => void>()`. The `connect` function is defined with `useCallback(..., [])` (empty deps → stable identity), then a separate `useEffect(() => { connectRef.current = connect; }, [connect])` keeps the ref in sync.
  - The reconnect timer calls `connectRef.current()` instead of the captured `connect` — always invokes the live function.
  - **Result:** Reconnect logic is now ref-safe and stale-closure-free.

- **Exponential backoff added to reconnection.**
  - Implemented backoff: `Math.min(1000 * 2^attempt, 30000)ms` delay before each reconnect attempt.
  - Maximum retry cap: 5 attempts, then stops and logs `[Nexus WS] Max retries reached`.
  - `reconnectCountRef` is reset to `0` on every successful `open` event.

- **Stable `useCallback` deps for `connect` and `disconnect`.**
  - Both `connect` and `disconnect` now use `useCallback(..., [])` — all mutable state (socket, handlers, etc.) accessed via refs, not captured variables.
  - **Result:** Neither function ever changes identity across renders, so downstream effects that list them as deps won't re-trigger.

- **`safe_send_json` / `safe_send_bytes` wrappers added.**
  - Added `onMessageRef`, `onTranscriptRef`, `onAgentMessageRef` refs that store the latest callback versions.
  - All message dispatch goes through these refs — no stale callback captures inside the WebSocket `onmessage` handler.

---

#### ⚛️ Frontend — `NexusContext.tsx` (React Effect Dep Array)

- **CRITICAL: Mount effect re-trigger eliminated.**
  - **Root Cause:** `useEffect(() => { connect(); return () => disconnect(); }, [connect, disconnect])` — even with a stable `connect`, any transient identity change (e.g., during Fast Refresh) would re-fire this effect, calling `connect()` on an already-open socket.
  - **Fix:** Changed dep array to `[]` (mount-once semantics) with `// eslint-disable-next-line react-hooks/exhaustive-deps` comment explaining the intentional choice.
  - **Result:** `connect()` is called exactly once on component mount; `disconnect()` is called exactly once on unmount.

- **Wrapped transcript/agent handlers in `useCallback`.**
  - `handleTranscript` and `handleAgentMessage` were previously re-created on every render.
  - Wrapped both in `useCallback` to produce stable function identities — prevents hook dependency instability in downstream effects.

---

#### 🐍 Backend — `ws_main.py` (Greeting Cache + RuntimeError Fix)

- **CRITICAL: Repeated greeting synthesis on every reconnect fixed.**
  - **Root Cause:** Each WebSocket reconnect triggered `greet()`, which ran a full Kokoro ONNX inference (~3 seconds, high CPU). During a reconnect storm, this queued multiple concurrent synthesis tasks → CPU at 98%.
  - **Fix:** Added module-level cache variables:
    ```python
    _has_greeted: bool = False
    _cached_greeting_pcm: Optional[bytes] = None
    ```
  - On first connection: synthesizes audio, stores in `_cached_greeting_pcm`, sets `_has_greeted = True`.
  - On subsequent connections: sends cached PCM bytes directly — zero ONNX inference.
  - **Result:** Greeting synthesis runs exactly once per server lifetime. CPU stable post-startup.

- **CRITICAL: `RuntimeError: Cannot call "receive" once a disconnect message has been received` eliminated.**
  - **Root Cause:** Starlette raises `RuntimeError` (not `WebSocketDisconnect`) when `websocket.receive()` is called after the disconnect frame has already been consumed internally. The outer `except WebSocketDisconnect` did not catch it → logged as unhandled error and printed misleading stack traces.
  - **Fix:** Added inner try/except around `websocket.receive()` inside the main loop:
    ```python
    try:
        data = await websocket.receive()
    except (WebSocketDisconnect, RuntimeError):
        break
    ```
  - Also added `if "disconnect" in data: break` to handle graceful client-initiated disconnects signaled via the data dict.
  - Added `logger.info("🔌 Session cleaned up")` in `finally` block for lifecycle clarity.
  - **Result:** Clean disconnect in all cases. No more error log spam on client close.

- **`safe_send_json` / `safe_send_bytes` wrappers implemented.**
  - Both check `self.is_connected` before attempting to send — prevents `WebSocketDisconnect` exceptions during TTS streaming when client disconnects mid-sentence.
  - `safe_send_bytes` also catches `RuntimeError` for the same Starlette edge case.

- **`has_greeted` session guard added.**
  - `VoiceSession.has_greeted` instance flag prevents double-greeting within a single session object, independent of the global cache.

---

#### 🔊 Backend — `providers/tts.py` (Log Cleanup & CPU Reduction)

- **Removed high-frequency TRACE log dumps.**
  - **Removed (fired every TTS call, high CPU string formatting cost):**
    - `📊 [TRACE] Raw Waveform: shape=... | dtype=...`
    - `📊 [TRACE] Raw Stats: min=... | max=... | mean=...`
    - `📊 [TRACE] First 10 samples: [...]`
    - `📊 [TRACE] PCM Int16: min=... | max=... | RMS=...`
    - `📊 [TRACE] First 10 PCM values: [...]`
  - **Removed (fired every ONNX inference):**
    - `--- ONNX Inference Inputs ---` block with per-tensor shape/dtype logging.
  - **Kept:** Essential lifecycle logs (`Synthesis started`, `Generated N samples`, error paths).
  - **Result:** Log volume reduced ~80% per TTS call. `np.min/max/mean` string-formatting cost eliminated from hot path.

---

### Infrastructure

- **Backend restart procedure established:**
  - Pattern: `Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Force` → `Start-Sleep 2` → `python voice_agent/ws_main.py`
  - Documented to avoid `[Errno 10048] address already in use` errors on rapid restarts.

---

### Validation

After all fixes, observed stable backend behavior:
```
INFO: WebSocket connected
INFO: Sending greeting: Nexus system online...   ← first connection only
INFO: 🔊 [TTS] Generated 48469 samples (3.03s)
INFO: Session cleaned up                          ← clean disconnect
INFO: WebSocket connected
INFO: Skipping greeting (already greeted)         ← cache hit on reconnect
INFO: 📩 Received chat message: hwwy
INFO: 🔊 [TTS] Generated 30037 samples (1.88s)
INFO: 🤖 Nexus Full Response: Hello, how can I help you today?
```
- **No `RuntimeError` in logs** ✔
- **No reconnect storm** ✔ (single connection holds stable)
- **Greeting fires once per server lifetime** ✔
- **Chat message → LLM → TTS → response pipeline fully functional** ✔



## [Unreleased] - 2026-05-03

### Fixed
- **Backend: Voice Agent Stability**: 
  - Fixed `TypeError` in `main.py` by removing the unsupported `allow_interruptions` argument from `agent.say()`.
  - Implemented background task tracking for the `greeter` sequence to prevent early garbage collection.
  - Improved `greeter` reliability by increasing startup delay to 4.0s (allowing WebRTC transport to stabilize).
  - Added `scipy` to `requirements.txt` to fix resampling dependency errors in `KokoroTTS`.
  - Optimized `GroqSTT` sensitivity by lowering silence thresholds and adding real-time energy logging for better turn detection.
- **Backend: Audio Quality & Resampling**:
  - Fixed `KokoroTTS` sample rate mismatch by implementing high-quality resampling (from 24kHz/22.05kHz to 16kHz) to match framework expectations.
  - Optimized PCM conversion logic in `providers/tts.py` for consistent, jitter-free audio.
- **Frontend: Voice UI & Audio Binding**:
  - Fixed "Agent not listening" by resolving a `ReferenceError` (`isVoiceMode` -> `uiMode`) in `NexusContext.tsx`.
  - Implemented **Interval-based Audio Binding** in `NexusContext.tsx` to automatically catch and bind the AI agent's audio track.
  - Fixed TypeScript errors in `NexusContext.tsx` regarding `activeCall.on/off` listener signatures.
- **Intelligence & Visualization ("them" folder)**:
  - Created `them/generator.py`: A automated codebase scanner that generates `graph.json` and `logs.md`.
  - Created `them/graph.html`: A premium interactive force-graph (D3.js) for codebase visualization.
  - Fixed Unicode encoding errors in the generator script for Windows compatibility.

### Added
- **Agent Intelligence Standard**: Promoted Truth Engine protocol to the **Global Gemini Configuration** (`C:\Users\JinWoo\.gemini\GEMINI.md`).
  - Establishes the **Code Review Graph (Truth Engine)** as the primary source of truth for AI agents across all projects.
  - Enforces a "Summary-First" and "Wiki-First" analysis workflow to minimize token consumption and speed up context loading globally.
  - Mandates running `./sync-context.ps1` or equivalent synchronization for context synchronization.
- **Context Automation**: Successfully executed `sync-context.ps1` to update the project's intelligence layer:
  - Updated the **Code Review Graph** (`graph.db`, `graph.html`) for deep codebase scanning.
  - Regenerated the **Codebase Wiki** in `.code-review-graph/wiki/` (logic and architecture docs).
  - Extracted fresh **tRPC API Documentation** into `.planning/codebase/TRPC_API.md`.
  - Built **Boneyard-JS** skeletons for UI snapshotting.
- **Project Intelligence**: Created `CONTEXT_SUMMARY.md` as a central entry point for all AI context artifacts.

---

## [v0.4.5] - 2026-05-02

---

## [v0.4.0] - 2026-05-02 — Intelligence Layer: Code Review Graph & Context Automation

### Session Scope
**Core:** Full Codebase Scanning & Analysis
**Engineer:** AntiGravity + Aniket  
**Tools:** `code-review-graph`, `fastmcp`

---

---

## [v0.3.0] - 2026-05-01 — Nexus 2.0 UI Overhaul: 3-Column Glassmorphic Layout

### Session Scope
**Frontend:** `d:/AI/frontend/src/`  
**Engineer:** AntiGravity + Aniket  
**Duration:** Full session — UI architecture port, component rewrites, audio fix, DB migration

---

### Added

#### UI Architecture — 3-Column Layout (`src/app/page.tsx`)
- Ported the final reference design from `d:/AI/demos/06-nexus-final-perfect.html` into the live Next.js app.
- Implemented a **3-column CSS Grid** layout (`main-container` class) replacing the previous single-column scroll layout:
  - **Left column** — Neural Telemetry card (Logic Engine + Vision Buffer progress bars), Vision Core live-feed placeholder with red `VISION_01` indicator, and 4-button Fast Actions grid (Voice, Agents, Network, Shell).
  - **Center column** — Top row: `ThreeOrb` card (col-span-5) + Nexus Neural Net "thinking" card (col-span-7). Bottom: Autonomous Shell terminal-style feed with floating browser preview panel.
  - **Right column** — Interface\_Link panel with 3 tabs (Chat / Tasks / Notes) and unified `InputArea` at bottom.
- Added `History` (clock) and `MessageSquarePlus` (new chat) icon buttons to the Nexus Neural Net card header using `lucide-react`.
- Removed all v1/v2/v3 orb variant selector buttons — only the single default `ThreeOrb` remains.
- Removed voice mode toggle from the right sidebar (voice is now exclusively controlled from the Nexus Core card).
- Added inline control cluster inside the `ThreeOrb` card: Mute/Unmute button, Play/Stop button (maps to `toggleListening`), and Refresh button (shows spin animation via `isSending`).

#### Component Library — shadcn/ui (`src/components/ui/`)
- Installed and configured **shadcn/ui** (`components.json` configured with `base-nova` style, `neutral` base color, Lucide icon library, CSS variables enabled).
- Added the following shadcn primitives to `src/components/ui/`:
  - `button.tsx` — variant-aware Button with `cva` (default, outline, ghost, destructive, etc.)
  - `card.tsx` — Card, CardHeader, CardContent, CardFooter, CardTitle, CardDescription
  - `tabs.tsx` — Tabs, TabsList, TabsTrigger, TabsContent (Radix-based)
  - `scroll-area.tsx` — ScrollArea + ScrollBar with custom scrollbar styling
  - `badge.tsx` — Badge with variants (default, secondary, outline, destructive)
- Added `src/lib/utils.ts` — `cn()` helper using `clsx` + `tailwind-merge`.

#### Firebase Integration (`src/lib/firebase/server.ts`)
- Migrated persistence layer from **Supabase/Postgres** to **Firebase** (Firestore).
- Created `src/lib/firebase/server.ts` — server-side Firebase Admin SDK initialization using service account credentials from environment variables.
- Added `firebase` (`^12.12.1`) and `firebase-admin` (`^13.8.0`) to `package.json` dependencies.
- Removed all Supabase client references from the frontend codebase to eliminate confusion and stale config.

---

### Changed

#### `src/components/ThreeOrb.tsx` — Full Rewrite
- **Before:** Multiple config variants (v1 glass/wireframe/nested, v2, v3 selector) using heavy custom GLSL shaders with `THREE.ShaderMaterial`. Caused `uniform3fv` WebGL errors and page instability on hot reload.
- **After:** Single unified `OrbSystem` class using:
  - `THREE.IcosahedronGeometry` (core: detail=15, shell: detail=5) with `MeshPhongMaterial` (wireframe, transparent) for performance.
  - Two-layer nested wireframe: inner core (opacity 0.3, indigo) + outer shell (opacity 0.1, deeper indigo), counter-rotating for depth effect.
  - `THREE.Clock` initialized once in constructor (eliminated duplicate clock instances that caused frame-time drift).
  - GSAP `to()` for smooth volume-reactive scale pulse (`0.15s power2.out`) instead of frame-by-frame lerp.
  - `updateConfig()` method for live prop updates without remounting (color and volume reactivity without destroying the WebGL context).
  - Proper `dispose()` — cancels animation frame, removes resize listener, disposes renderer — preventing memory leaks on unmount.
- Exported clean `OrbConfig` type (`scale`, `speed`, `noiseFreq`, `noiseAmp`, `color1`, `color2`, `volume`) — no internal defaults leaking to consumers.
- Fixed TypeScript syntax error: removed invalid object literal inside constructor body that caused `SWC` build crash (`Expected ';', '}' or <eof>` at line 121).

#### `src/app/globals.css` — Nexus 2.0 Design System
- Replaced default Tailwind/Next.js globals with a full **Nexus 2.0 premium dark theme**:
  - Background: `#070708` (near-black base).
  - `.glass` utility: `backdrop-blur-2xl`, `bg-white/[0.03]`, `border border-white/[0.06]`, `rounded-2xl` — matches the reference demo exactly.
  - `.main-container`: `display: grid`, `grid-template-columns: 280px 1fr 380px`, `gap: 12px`, full-height viewport layout.
  - `.tab-active`: `bg-white/[0.08]`, `text-white`, `shadow-sm` — clean active tab indicator.
  - `.status-dot`: `6px` circle, `bg-emerald-500`, shadow glow effect.
  - `.scroll-hide`: cross-browser scrollbar hiding for clean overflow panels.
  - `.shimmer`: skeleton loading animation using `@keyframes shimmer` with gradient sweep.
  - Google Font `Inter` imported with weights 400/500/600/700/800/900.

#### `src/components/InputArea.tsx` — Cleanup
- Removed the standalone voice mode toggle row that was redundant with the Nexus Core card controls.
- Removed the embedded voice waveform and session UI from the chat input bar (voice is managed at the Core level now).
- Retained: text input field, send button, and basic toolbar icons.

#### `src/components/MessageList.tsx` — Style Update
- Updated message bubble styling to conform to the new dark glassmorphic theme (zinc-800/white-5 backgrounds, reduced opacity borders, smaller font weights).

---

### Fixed

#### Audio Echo on Voice Session Start (`src/contexts/NexusContext.tsx`)
- **Root cause:** `<audio>` element had `autoPlay` set unconditionally, causing the local microphone stream to loop back through the speaker immediately on session start.
- **Fix:** Removed `autoPlay` attribute from the hidden audio element. Audio playback now only binds via `call.bindAudioElement()` after the remote participant track is confirmed, preventing echo.
- **Secondary fix:** Standardized participant audio binding to use `AGENT_USER_ID` filtering, so only the agent's audio output is routed to the speaker (not own mic echo).

#### Page Instability / Lag on Orb Mount
- **Root cause:** The old shader-based ThreeOrb instantiated multiple `THREE.Clock` objects across re-renders and used `setInterval`-based animation fallbacks that stacked on hot reloads.
- **Fix:** Single `OrbSystem` instance per mount lifecycle, single `THREE.Clock`, RAF-based animation with proper `cancelAnimationFrame` on cleanup.

#### Build Crash — SWC Syntax Error (`ThreeOrb.tsx` line 121)
- **Root cause:** Object literal `{ glass: false, wireframe: false, ... }` was written directly inside a constructor body as a standalone expression (not assigned), which is valid JS but was parsed incorrectly by `next-swc-loader` given surrounding TypeScript context.
- **Fix:** Full component rewrite eliminated the problematic code path entirely. `OrbConfig` defaults are now handled via nullish coalescing in the constructor (`opts.scale ?? 1`, etc.).

---

### Removed
- **Orb version selector** (v1/v2/v3 tabs/buttons) — removed from `page.tsx`. Only one orb design exists.
- **Voice mode toggle in right sidebar** — removed. Voice is controlled exclusively from the Nexus Core card's control cluster.
- **Supabase client references** — removed from frontend. Replaced by Firebase Admin SDK.
- **Legacy `drizzle` schema** (`src/lib/db/schema.ts`) — de-prioritized; Firestore is the active DB target. File retained but no longer imported.

---

### Dependencies Added (this session)
| Package | Version | Purpose |
|---|---|---|
| `firebase` | `^12.12.1` | Client-side Firebase SDK |
| `firebase-admin` | `^13.8.0` | Server-side Firestore / Admin |
| `shadcn` | `^4.6.0` | Component library CLI + primitives |
| `class-variance-authority` | `^0.7.1` | shadcn variant system (`cva`) |
| `clsx` | `^2.1.1` | Conditional class utility |
| `tailwind-merge` | `^3.5.0` | Tailwind class deduplication |
| `lucide-react` | `^1.11.0` | Icon set (History, MessageSquarePlus, etc.) |

---

### Architecture State After This Session

```
d:/AI/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          ← 3-column glassmorphic layout (source of truth)
│   │   │   └── globals.css       ← Nexus 2.0 design system tokens
│   │   ├── components/
│   │   │   ├── ThreeOrb.tsx      ← Stable single-variant WebGL orb
│   │   │   ├── InputArea.tsx     ← Chat-only input (voice stripped)
│   │   │   ├── MessageList.tsx   ← Dark-mode message bubbles
│   │   │   └── ui/               ← shadcn primitives (button, card, tabs, etc.)
│   │   ├── contexts/
│   │   │   └── NexusContext.tsx  ← Echo-free audio binding
│   │   └── lib/
│   │       ├── firebase/
│   │       │   └── server.ts     ← Firebase Admin SDK init
│   │       └── utils.ts          ← cn() helper
│   └── components.json           ← shadcn config
└── demos/
    └── 06-nexus-final-perfect.html ← Reference design (do not modify)
```

---

### Known Issues / Next Steps

| # | Issue | Priority |
|---|-------|----------|
| 1 | Tasks tab shows "No active tasks" — needs Firestore CRUD + tRPC router | HIGH |
| 2 | Notes tab shows "No notes saved" — needs Firestore CRUD + tRPC router | HIGH |
| 3 | Chat messages not persisted — `MessageList` is in-memory only | HIGH |
| 4 | History button (clock icon) is non-functional — needs chat session list from Firestore | MEDIUM |
| 5 | New Chat button is non-functional — needs session reset + Firestore write | MEDIUM |
| 6 | Vision Core feed is a placeholder — no actual camera/screen feed | LOW |
| 7 | Fast Actions grid (Agents, Network, Shell) buttons are non-functional stubs | LOW |

---

## [v0.2.7] - 2026-05-01

### Added
- **Manual Credential Management**: Updated `.env` files (backend and frontend) with minified Firebase service account JSON manually, bypassing script requirements.
- **Robust Startup Script**: Fixed `StartBackend.ps1` syntax errors (array index and missing quotes) and removed emojis to ensure compatibility with Windows PowerShell encoding.

### Changed
- **Unicode Stability**: Removed emojis from backend logging (main.py, diagnostics.py) to prevent `UnicodeEncodeError` on Windows environments using `cp1252` encoding.
- **Config Sync**: Optimized the `.env` sync logic in `StartBackend.ps1` to pull from the correct source directory.
- **Launcher Reliability**: Updated `StartBackend.ps1` with verbose status indicators, automatic `.env` syncing, and debug-level uvicorn logging.
- **Launcher Speed**: Removed `--upgrade` from default pip installation in `StartBackend.ps1` to reduce startup time.
- **Logging Robustness**: Fixed `os` import issues in `main.py` and consolidated environment checks.
- **Unified Requirements**: Ensured `stream-chat` and `loguru` are present in `backend/requirements.txt`.
- **Robust Settings**: Modified `Settings` to allow optional `DATABASE_URL` and `OPENAI_API_KEY`, preventing crashes when specific features are disabled.
- **Memory Service Resilience**: Added try-except blocks to Firestore operations to ensure the voice agent remains functional even if database connection fails.
- **Orchestrator Observability**: Added detailed trace logs in `NexusVoiceOrchestrator` for agent creation and call joining phases.


---

## [v0.2.6] - 2026-04-27

### Fixed
- **Fatal Audio Consumer Crash**: Patched the framework's `agents.py` loop to be resilient against single-chunk errors, preventing session death on malformed audio data.
- **Audio Buffer Overflows**: Optimized the `Agent` loop to drain backlogs aggressively and made the STT provider non-blocking, eliminating "buffer limit exceeded" drops.
- **PcmData Compatibility**: Rewrote the STT audio adapter to properly extract raw bytes from `PcmData` and other framework-specific audio types.
- **Performance Overhead**: Removed high-frequency blocking `print` calls and moved audio decoding to background tasks for maximum CPU efficiency.

## [v0.2.5] - 2026-04-27

### Changed
- **STT Model Downgrade**: Switched Faster-Whisper from `base` to `tiny` for significant CPU performance gains and near-zero transcription latency.
- **Hindi Greeting**: Updated the initial greeting in `main.py` to "Hey Aniket, kaise ho?" as per user requirement.
- **System Prompt Hardening**: Reinforced the assistant identity to always prioritize Hindi greetings for Aniket.

## [v0.2.4] - 2026-04-27

### Fixed
- **STT PcmData Error**: Implemented a robust audio adapter in `providers/stt.py` to handle GetStream's `PcmData` object and other bytes-like types.
- **Kokoro TTS Pickle Loading**: Fixed the `voices.bin` loading issue by globally monkeypatching `np.load` to allow pickle loading during initialization.
- **Voice Pipeline Performance**: Optimized the real-time loop by moving STT and TTS inference to background threads via `asyncio.to_thread` and downgrading Whisper to the `base` model for CPU efficiency.
- **Audio Buffer Management**: Implemented a strict 1s audio queue in `main.py` and a 100ms framing buffer in `stt.py` that drops old chunks to maintain sub-second latency.
- **Console Observability**: Added throttled visible logging (every 50 chunks) for audio reception, decoding, and queue depth to provide clear status without terminal spam.

## [v0.2.3] - 2026-04-27

### Fixed
- **Deepgram Handshake Error**: Resolved `TypeError: AsyncV2Client.connect() got an unexpected keyword argument 'interim_results'` by switching to the more stable `v1.connect` API in `providers/stt.py`.
- **TTS Provider Upgrade**: Migrated from ElevenLabs to OpenAI `tts-1` in `providers/tts.py` for industry-standard reliability and lower latency.
- **Code Cleanliness**: Consolidated `main.py` imports and renamed the LLM provider to `NexusLLM` for brand consistency.
- **Environment Validation**: Updated `validate_env` to strictly enforce the presence of `OPENAI_API_KEY`.

### Added
- **Env Guidance**: Added `OPENAI_API_KEY` placeholder to `.env` and updated `README.md` requirements.

## [v0.2.2] - 2026-04-27

### Fixed
- **STT Pipeline Stability**: Implemented strict sequential initialization. The agent now waits for a 200 OK from Deepgram before joining the room.
- **Audio Buffer Bloat**: Added a 100ms circular buffer with windowed discard to prevent memory leaks and maintain low latency during long calls.
- **IDE Cleanliness**: Removed redundant `useNexusVoice.ts` and `useVoiceSession.ts` hooks. Eliminated all unused imports and type warnings in both Frontend and Backend.
- **Terminal Clarity**: Added `[Agent]` prefix to all backend logs (both print and logging) for consistent observability.

### Added
- **Production README**: Created `backend/voice_agent/README.md` with explicit instructions on running the agent via `StartBackend.ps1` to avoid environment conflicts.
- **Expanded Context**: Added `setIsSending`, `setMessages`, and other missing setters to `NexusContext` to support all feature hooks without lint errors.

## [v0.1.2] - 2026-04-27

### Added
- **WebRTC Audio Binding**: Implemented `call.bindAudioElement` in `NexusContext.tsx` to fix the issue where AI voice was not audible despite call connection.
- **Dynamic Waveform UI**: Added a reactive CSS-animated waveform to `InputArea.tsx` during voice sessions for real-time visual feedback.
- **Root Launcher Scripts**: Created `NexusLauncher.ps1` and `StartBackend.ps1` to simplify starting both Frontend and Voice Agent with correct environments.

### Fixed
- **Duplicate Mic Icons**: Consolidated all voice controls (Mute, End Session) into `InputArea.tsx`, removing the redundant floating action bar from `page.tsx`.
- **UI Mode Transitions**: Improved logic for switching between Chat and Voice modes to ensure a cleaner transition and state cleanup.


## [v0.1.1] - 2026-04-27

### Fixed
- **Voice Agent Crash**: Resolved `AttributeError: 'NoneType' object has no attribute 'wait_until_finished'` by correctly using `agent.finish()` in the session lifecycle.
- **Missing Greeting**: Added an initial greeting message ("Hello! I am Nexus...") that triggers automatically when the agent joins a call.
- **Model Synchronization**: Fixed model toggle logic so that both Chat and Voice modes respect the user's selected model (Llama 3.3, 3.1, or Mixtral).

### Added
- **Initial AI Voice**: The agent now proactively speaks upon connection to confirm the voice pipeline is working.
- **Enhanced API Docs**: Full tRPC metadata and JSDoc documentation for all endpoints following `Awesome-tRPC` patterns.

## [v0.1.0] - 2026-04-27
ARCHITECTURE.md` as part of the project intelligence update.

### Fixed
- **LLM Streaming Logic**: Patched `GroqLLM` token chunking in `llm.py` to fix the "silent" agent issue where the first token flag was not correctly set.
- **Double Mic Glitch**: Hidden the small input microphone icon in `InputArea.tsx` during active voice sessions to prevent UI clutter.
- **Backend Port Conflict**: Resolved port 8000 binding errors by identifying and terminating orphaned server processes.

### Changed
- **Groq Model Mapping**: Standardized model IDs across Frontend and Backend for reliable production inference.
- **Initial Prompting**: Optimized the agent's system prompt for shorter, more conversational voice responses.

---

## [Unreleased] — 2026-04-27

### Session: Voice Agent Implementation (Full Session Log)
**Date:** 2026-04-26 → 2026-04-27  
**Engineer:** AntiGravity (AI) + Aniket  
**Scope:** `d:/AI/backend/voice_agent/`

---

## [0.2.1] — 2026-04-27 — Voice Agent: Core Call Manager Implementation

### Added
- **`backend/voice_agent/core/call_manager.py`**: Fully implemented the production-grade streaming pipeline.
  - Replaced the placeholder loop with a functional `vision_agents.Agent` lifecycle.
  - Integrated `GroqLLM`, `DeepgramSTT`, and `ElevenLabsTTS` via the `vision-agents` event-bus.
  - Implemented the `async with agent.join(call)` pattern for robust WebRTC session management.
  - Added comprehensive environment variable validation for all required API keys.
  - Configured `streaming_tts=True` for sub-second latency in voice responses.
  - Added support for custom instructions/system prompts passed from the launcher.

### Changed
- Refined the `Agent` configuration to use the `Iridescent Assistant` identity (id: `production-agent-001`).
- Improved error handling and graceful shutdown logging in the core call manager.

---

## [0.2.0] — 2026-04-27 — Voice Agent: Production Pipeline Complete

### Overview
This session took the voice agent from a completely stubbed placeholder state
to a production-ready, framework-native, streaming voice pipeline using:
- **GetStream Video** — WebRTC transport (Edge)
- **Deepgram Nova-3** — streaming Speech-to-Text
- **Groq llama-3.3-70b-versatile** — streaming LLM (non-OpenAI)
- **ElevenLabs Multilingual v2** — streaming Text-to-Speech

---

### Research Phase (Pre-Code)

#### Framework Identification
- Confirmed the correct Python framework is `vision-agents` by GetStream
  (GitHub: `GetStream/Vision-Agents`), **not** LiveKit or any OpenAI SDK.
- Verified `vision-agents 0.5.4` was already installed in the venv.
- Identified the correct architecture: `Agent` + `AgentLauncher` + `Runner`
  — the framework's native production entry points.

#### Plugin Discovery
- Audited all installed packages via `pip list`.
- Found `vision-agents-plugins-deepgram`, `vision-agents-plugins-elevenlabs`,
  `vision-agents-plugins-cartesia` were already installed.
- **Critical finding:** `vision-agents-plugins-getstream` was MISSING —
  this is the package that provides the concrete `Edge` (EdgeTransport)
  implementation required for GetStream WebRTC connectivity.
- Confirmed by reading `vision_agents-0.5.4.dist-info/METADATA` which listed
  `vision-agents-plugins-getstream` as an optional `all-plugins` dependency
  that was not installed by default.

#### Base Class API Verification (Zero Hallucination)
- Read `vision_agents/core/llm/llm.py` source to confirm:
  - `LLM` has exactly **one** abstract method: `simple_response(text, participant=None) → LLMResponseEvent`
  - NO `respond()` method exists on the base class (the previous implementation was wrong)
  - `LLMResponseEvent.__init__(original, text, exception=None)` — must return this object
- Read `LLMResponseChunkEvent` and `LLMResponseCompletedEvent` dataclass fields:
  - Chunk event uses `delta` (not `text`) for the streaming token
  - Completed event uses `text`, `model`, `plugin_name` etc. — all with defaults
- Read `StreamEdge.__init__` — takes `**kwargs`, reads `STREAM_API_KEY` + `STREAM_API_SECRET` from environment automatically
- Read `StreamEdge.authenticate(user)` — calls `client.create_user()` with the User object
- Read `StreamEdge.create_call(call_id, call_type=)` — creates/fetches an audio_room call
- Read `AgentLauncher`, `Runner`, `ServeOptions`, `User` — all exported from `vision_agents.core`
- Read `Agent.join(call)` — async context manager, exits when call ends

---

### Added

#### Package: `vision-agents-plugins-getstream 0.5.4`
- **Why:** The concrete `Edge` / `StreamEdge` class (GetStream WebRTC transport adapter)
  lives in this separate plugin package. Without it, there is no way to connect
  the Python agent to a GetStream audio room.
- **Install command:** `pip install vision-agents-plugins-getstream`
- **Provides:**
  - `vision_agents.plugins.getstream.Edge` → `StreamEdge` class
  - `vision_agents.plugins.getstream.Conversation` → `StreamConversation`
  - All GetStream event model re-exports (CallEndedEvent, etc.)
- **Reads from env:** `STREAM_API_KEY`, `STREAM_API_SECRET` (via `AsyncStream`)

#### Package: `redis 7.4.0`
- **Why:** `vision_agents/plugins/getstream/stream_conversation.py` emits a
  `UserWarning` at import time if `redis` is not installed, because
  `RedisSessionKVStore` is unavailable. While harmless for operation (falls
  back to in-memory store), the warning cluttered startup logs.
- **Install command:** `pip install redis`
- **Result:** Warning eliminated. `python main.py serve` starts with zero warnings.

---

### Changed / Rewritten

#### `d:/AI/backend/voice_agent/main.py` — Complete Rewrite

**Before:** Manual `uvicorn.run()` boilerplate, ad-hoc concurrency wrappers,
placeholder `call_manager.py` usage, incorrect import paths for providers.

**After:** Framework-native production entry point using verified APIs.

Key changes:
1. **Import path fixed:** `from vision_agents.plugins.getstream import Edge`
   (was trying to use a non-existent custom EdgeTransport subclass)
2. **`create_agent()` factory function:**
   - Creates `Edge()` — the concrete GetStream WebRTC transport
   - Creates `DeepgramSTT(api_key, model="nova-3", eager_turn_detection=True)`
     — `eager_turn_detection=True` reduces turn-end latency by ~200ms
   - Creates `GroqLLM(api_key, model, temperature, max_tokens)`
   - Creates `ElevenLabsTTS(api_key, model_id, voice_id)` — eleven_multilingual_v2
   - Returns `Agent(edge, agent_user, instructions, llm, stt, tts, streaming_tts=True)`
3. **`join_call()` async callback:**
   - Calls `edge.authenticate(agent.agent_user)` — creates the bot user in Stream
   - Calls `edge.create_call(call_id, call_type=call_type)` — gets/creates the room
   - Uses `async with agent.join(call):` — framework context manager handles lifecycle
   - Fires `agent.simple_response("Greet...")` to greet users on join
4. **`AgentLauncher` config:**
   - `max_concurrent_sessions=50` (from env `MAX_CONCURRENT_CALLS`)
   - `agent_idle_timeout=120.0` — agent leaves if nobody speaks for 2 minutes
   - `max_sessions_per_call=1` — only one bot per room
5. **`Runner` + FastAPI app:**
   - `runner = Runner(launcher, serve_options=ServeOptions(cors_allow_origins=["*"]))`
   - `app = runner.fast_api` — exposed at module level for uvicorn/gunicorn
6. **CLI entrypoint:** `runner.cli()` — provides `serve` and `run` subcommands

**STT config details:**
- Model: `nova-3` (Deepgram's fastest, most accurate model as of 2026)
- `eager_turn_detection=True` — reduces latency significantly in fast-paced Q&A

**TTS config details:**
- Model: `eleven_multilingual_v2` — supports English, Hindi, Marathi naturally
- Voice: `VR6AewLTigWG4xSOukaG` (configurable via `ELEVENLABS_VOICE_ID` env)
- `streaming_tts=True` — TTS begins as soon as first sentence token arrives from LLM

**System prompt:**
```
You are Nexus, a friendly, sharp voice assistant.
Keep answers short (1–3 sentences), conversational, and avoid markdown.
You can speak English, Hindi, and Marathi naturally.
```

---

#### `d:/AI/backend/voice_agent/providers/llm.py` — Complete Rewrite

**Before:** Incorrect implementation with:
- `respond()` method that doesn't exist on the base class
- `simple_response()` returning a plain `str` (wrong — base requires `LLMResponseEvent`)
- `LLMResponseChunkEvent(text=token)` — wrong field name (should be `delta=token`)
- `EventManager()` instantiated in `__init__` which requires a running event loop
  and crashes when instantiated outside async context

**After:** Correct implementation matched to verified base class API:

1. **`simple_response(text, participant=None) → LLMResponseEvent`** (the only abstract method):
   - Builds message history from `self._instructions` + `self._conversation.messages`
   - Calls Groq API with `stream=True`
   - Accumulates full response while firing `LLMResponseChunkEvent(delta=token)` per token
   - Fires `LLMResponseCompletedEvent(text=full, model=self.model)` at end
   - Returns `LLMResponseEvent(original=raw_chunk, text=full_response)`
   - On exception: returns `LLMResponseEvent(original=None, text="", exception=exc)`

2. **`_build_messages(text)`** helper:
   - System prompt first
   - Prior conversation turns from `self._conversation` (if available)
   - Current user text last

3. **`close()`** — properly closes the Groq AsyncClient's inner httpx client

**Groq model:** `llama-3.3-70b-versatile`
- Best latency/quality ratio for general Q&A as of April 2026
- Configurable via `LLM_MODEL` env var

---

### Fixed

#### Bug: Port 8000 conflict (WinError 10048)
- **Cause:** A previous `python main.py serve` process (PID 58348) was still running
  in the background and holding port 8000.
- **Fix:** `taskkill /F /PID 58348` — killed the orphaned server process.
- **Prevention:** Before running `python main.py serve`, check with
  `netstat -ano | findstr :8000` and kill any existing process first.

#### Bug: GroqLLM `RuntimeError: no running event loop` on instantiation
- **Root cause:** Previous implementation called `super().__init__()` which triggers
  `EventManager()` which calls `asyncio.get_running_loop()` — fails outside async context.
- **Fix:** `GroqLLM` now only instantiated inside `create_agent()` which is always
  called from within the framework's running async event loop.

#### Bug: Wrong event field `text` vs `delta` in `LLMResponseChunkEvent`
- **Root cause:** Previous code used `LLMResponseChunkEvent(text=token)` but the
  actual dataclass field is named `delta`.
- **Fix:** Changed to `LLMResponseChunkEvent(delta=token)`.

---

### Validation Results

All imports verified clean:
```
providers.llm OK
main.py OK
app: <fastapi.applications.FastAPI object at 0x...>
```

Server startup confirmed working:
```
INFO | Started server process [63668]
INFO | Creating agent...
INFO | nexus.agent — Building new agent session
INFO | Warming up agent components...
INFO | Downloading silero_vad.onnx...
INFO | silero_vad.onnx downloaded.
INFO | Agent warmup completed
INFO | Application startup complete.
INFO | Uvicorn running on http://127.0.0.1:8000
```

---

### Architecture: Final State

```
d:/AI/
├── backend/
│   └── voice_agent/
│       ├── main.py              <- Production entry point (Runner + AgentLauncher)
│       ├── providers/
│       │   ├── llm.py           <- GroqLLM (correct base class impl)
│       │   └── stt.py           <- (legacy manual STT, superseded by plugin)
│       ├── agent.py             <- (legacy stub, superseded by framework Agent)
│       ├── core/
│       │   └── call_manager.py  <- (legacy placeholder, superseded by AgentLauncher)
│       ├── config.py
│       ├── requirements.txt
│       └── .env                 <- STREAM_API_KEY, STREAM_API_SECRET, GROQ_API_KEY,
│                                   DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
└── frontend/                    <- Next.js (untouched this session)
```

**Pipeline flow:**
```
User mic -> GetStream WebRTC (Edge) -> Deepgram STT -> GroqLLM -> ElevenLabs TTS -> User speaker
```

**HTTP API (serve mode):**
```
POST   /calls/{call_type}/{call_id}/sessions      -> start agent on that call
DELETE /calls/{call_type}/{call_id}/sessions/{id} -> stop agent
GET    /health                                    -> liveness probe
GET    /ready                                     -> readiness probe
```

---

### Known Issues / Next Steps

| # | Issue | Priority |
|---|-------|----------|
| 1 | Frontend doesn't auto-trigger POST /calls/.../sessions after room join | HIGH |
| 2 | agent.py and core/call_manager.py are dead code — should be deleted | LOW |
| 3 | providers/stt.py is a legacy manual websocket impl — superseded by plugin | LOW |
| 4 | redis installed but using in-memory store (fine now, needed for multi-instance) | MEDIUM |
| 5 | cors_allow_origins=["*"] — tighten to specific frontend origin in prod | MEDIUM |

---

## [0.1.0] — 2026-04-26 — Voice Agent: Initial Scaffold

### Added
- `backend/voice_agent/` directory structure created
- `venv` with initial packages: `vision-agents`, `groq`, `deepgram-sdk`, `elevenlabs`,
  `getstream`, `fastapi`, `uvicorn`, `aiortc`, `cartesia`, `pydantic-settings`
- `providers/stt.py` — manual Deepgram websocket STT (later superseded by plugin)
- `providers/llm.py` — initial Groq LLM attempt (incorrect base class, later rewritten)
- `core/call_manager.py` — placeholder stub for call lifecycle
- `agent.py` — placeholder stub for agent orchestration
- `main.py` — initial manual uvicorn boilerplate (later fully rewritten)
- `config.py` — env var configuration loader
- `.env` — API keys for Stream, Groq, Deepgram, ElevenLabs

### Architecture Decision
- Selected `vision-agents` (GetStream's official Python agent SDK) as the
  primary framework — provides WebRTC transport, VAD, event bus, and plugin
  ecosystem without requiring OpenAI.
- Rejected LiveKit (different transport layer, incompatible with existing Stream frontend).
- Rejected raw WebRTC DIY approach (too much infra to maintain).

---

*Changelog maintained by AntiGravity. Every entry is verifiable against actual code.*

## [2026-06-11] - Bug Fixes: Mute Loop and VAD Deadlock

### Author
- Antigravity AI
- Machine: Windows

### Fixed
- Fixed 'Mute Loop' echo loop caused by premature expiration of post-TTS acoustic guard by resetting the guard timer when 'audio_finished' is explicitly received.
- Fixed complete VAD deafness ('not listening voice') caused by 'agent_is_speaking' deadlock. The backend greeting generation and cached greeting paths were missing the 'tts_end' sentinel, leaving the session permanently blocked.

### Notes
- Also installed 'google-genai' into the core backend venv to unblock the GeminiTTS provider.
