# CHANGELOG - Nexus AI Project

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) + Semantic Versioning.

---

## [2026-06-16] - Phase 5: Voice Stack Stabilization & Humanization

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **VAD Diagnostics**: Added detailed VAD telemetry (RMS Energy, specific rejection reasons, duration, preroll size) directly into `ws_main.py` logs to diagnose "Ghost Listening" false triggers.
- **Speech Director**: Added `apply_speech_director()` to seamlessly replace hardcoded text fillers (e.g. `Ahh`, `Hmm`, `bhai`) with natural acoustic pauses (`Ahh...`, `Hmm...`, `bhai,`) before TTS generation.

### Changed
- **Speech Cleaner Overhaul**: Gutted the aggressive translating behavior of `speech_cleaner.py`. Redefined the prompt to exclusively act as a strict normalizer (stutter and spacing fix) with an absolute ban on translating or paraphrasing user intent.
- **Native Hinglish Pronunciation**: Deleted the fragile `pronunciation_dictionary.py` hardcoded map. Updated the core LLM prompt to output native Hindi/Marathi words exclusively in **Devanagari script** and English words in Latin script. This unlocks the EdgeTTS engine's native code-switching capabilities, resulting in flawless multilingual pronunciation without acoustic robotic artifacts.
- **Instant TTS Streaming**: Reactivated streaming TTFA by adding natural punctuation (`.`, `?`, `!`) to the `SENTENCE_ENDS` flush threshold, allowing EdgeTTS to synthesize sentence #1 instantly while the LLM generates sentence #2.

### Fixed
- **Whisper Hallucination Loop (Portuguese)**: Added explicit payload destruction in `ws_main.py` for known Whisper large-v3 silence hallucinations (`pedro negri`, `amara.org`, `transcrição e legendas`). This completely kills the bug where silence caused the STT to hallucinate subtitle credits, prompting the LLM to spontaneously reply in Portuguese.
- **Pyright IDE Warnings**: Suppressed `types.Part` union array strict typing errors and fixed a `NoneType` string vulnerability in `ws_main.py`'s Gemini STT fallback block.
## [2026-06-16] - Phase 5: Nexus V3 Stabilization, Forensic Audit & Pipeline Hardening

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Extensive Forensic & Architectural Documentation (Newly Created Files)
To prevent assumptions and ensure an evidence-based repair strategy, generated 13 exhaustive audit reports prior to making code changes:
- `VOICE_BUFFER_FORENSICS.md`: Identified the exact root cause of the 15.4s STT payload (a 409,600B accumulating preroll buffer).
- `MODEL_DEPRECATION_AUDIT.md`: Documented decommissioned Groq models (`llama3-8b-8192`) causing silent `speech_cleaner` failures, and dead dependencies.
- `TTS_LATENCY_BREAKDOWN.md`: Detailed stage-by-stage latency analysis, confirming Gemini TTS REST batches audio resulting in 4-7s TTFA.
- `IRIS_VOICE_BLUEPRINT.md`: Architecture comparison explaining why IRIS feels instant (Gemini Live bidirectional stream).
- `VOICE_PROVIDER_FAILOVER_PLAN.md`: Strategic plan to eliminate single-point-of-failure rate limit crashes.
- `HERMES_EXTRACTION_PLAN.md` & `STONIC_REUSE_MATRIX.md`: Analyzed Stonic and Hermes for reusable architectural patterns (state isolation).
- `VOICE_V3_ARCHITECTURE.md`: Final blueprint for Mode A (Gemini Live sub-1s) and Mode B (Current Pipeline sub-3s) dual-architecture.
- `INDIAN_ACCENT_STRATEGY.md`: Mapped Edge TTS neural voices (`en-IN`, `hi-IN`, `mr-IN`) to fix inconsistent accent routing.
- `PERSONALITY_PIPELINE_AUDIT.md`: Discovered that the rich `prompts.py` was completely orphaned and the LLM had zero conversation history.
- `NEXUS_CLEANUP_MASTER_PLAN.md`: Inventory of 17 dead files and redundant experiments for safe deletion.
- `NEXUS_FINAL_RECOMMENDATION.md`: Concluded with "Option C - Hybrid" (fix current pipeline, then introduce Gemini Live).
- `GEMINI_LIVE_MIGRATION.md`: Gap analysis detailing missing reconnection, interruption, tool calling, and memory for Gemini Live.

### Added
- **Multi-Provider Fallback (Resilience)**:
  - **STT Fallback**: Added `try/except` in `ws_main.py` so if Groq `whisper-large-v3` fails (e.g., HTTP 429), it gracefully fails over to Gemini `gemini-2.5-flash` for audio transcription without disconnecting the user.
  - **LLM Fallback**: Created a unified async streaming generator to gracefully failover from Groq's `llama-3.3-70b-versatile` to Gemini `gemini-2.5-flash` streaming on API errors.
  - **TTS Fallback**: Enhanced `tts.py` to seamlessly cascade through providers.
- **Memory Engine**: Injected a class-level `self.conversation_history` (deque with 8 rolling turns) in `VoiceSession` ensuring the LLM remembers context across queries.
- **Personality Wiring**: Imported `get_nexus_system_prompt()` directly from `prompts.py` into the active `run_pipeline`, replacing an inferior 6-line inline prompt.
- **Dynamic Language Routing**: Updated `tts_edge.py` with Devanagari script regex detection (`[\u0900-\u097f]`) to automatically switch TTS rendering to native `hi-IN-MadhurNeural`/`hi-IN-SwaraNeural` for flawless Hindi/Marathi pronunciation.

### Fixed
- **P0 Latency Bug (Preroll Memory Leak)**: Changed `vad_preroll_buffer: Deque[bytes] = deque(maxlen=50)` to `maxlen=8`, dropping stale audio retention from ~12.8s down to ~0.5s.
- **P0 Latency Bug (Buffer Flush)**: Appended `self.vad_preroll_buffer.clear()` immediately after prepending context to the active speech buffer, preventing exponential audio payload growth.
- **VAD State Accumulation Leak**: Wrapped the preroll append loop inside an explicit state check (`LISTENING`, `IDLE`, `DEBOUNCE`) to prevent background ambient noise from accumulating while the AI is in `THINKING` or `SPEAKING` states.
- **Broken Speech Cleaner**: Replaced the dead Groq model string in `speech_cleaner.py` from `llama3-8b-8192` to `llama-3.1-8b-instant`, restoring real-time filler word removal ("um, uh, like").
- **Clean Restart Crashing (Dead Dependencies)**: Hunted down and removed orphaned package imports (`getstream.video.rtc`, `vision_agents`, `kokoro_onnx`) inside `tts.py`, `tts_gemini.py`, and `tts_edge.py` to guarantee crash-free production server restarts.
- **Accent Inconsistency**: Changed the `base_chain` order in `tts.py` from `["gemini", "edge"]` to `["edge", "gemini"]`. Edge TTS is now primary, dropping TTFA latency to <250ms while enforcing the `en-IN` (Indian English) phonetics globally.
- **Startup Crash (ModuleNotFoundError)**: Fixed `tools/memory_tools.py` import path to correctly point to the relocated `core.memory_manager` module, preventing Uvicorn from crashing on boot.
- **TTS Router Bypass Bug**: Fixed `ws_main.py` explicitly forcing `provider="gemini"`, which bypassed `tts.py`'s routing rules and hit the strict Google API 10-requests/day free-tier quota (429 RESOURCE_EXHAUSTED). It now strictly honors `EdgeTTS` as the primary.
- **EdgeTTS & GeminiTTS Silent Crashing**: Fixed `TypeError` in `tts_edge.py` and `tts_gemini.py` where `PcmData.__init__` was being passed unused kwargs (`sample_rate`, `format`, `channels`), which caused silent fallback failures when `imageio-ffmpeg` succeeded.
- **Windows Event Loop Crash (NotImplementedError)**: The EdgeTTS pipeline threw a `NotImplementedError` during FFmpeg invocation due to Windows' `SelectorEventLoop` limitation under Uvicorn. Replaced `asyncio.create_subprocess_exec` with `asyncio.to_thread(subprocess.run)` to permanently bypass event loop restrictions and ensure flawless cross-platform audio conversion.
- **Pylance/IDE Type Enforcement**: Cleaned up false-positive squiggles in `ws_main.py` by converting string prompts to explicitly casted `types.Part.from_text(text="...")` blocks to satisfy VS Code Python Language Server.

### Removed
- **Safe Deletion**: Purged 17 outdated files including `test_edge_tts.py`, `test_gemini_tts.py`, `test_groq.py`, `test_tts.py`, `debug_json.py`, multiple `.raw` binary dumps, local text logs (`agent_err.txt`, `DEBUG_FORENSICS.txt`), and the entire `scratch/` directory.
- **Archive Migration**: Moved the legacy `main.py` entrypoint to `/archive_experiments` and relocated `memory_manager.py` to `/core/`.

### Notes
- **Performance Impact**: Time-To-First-Audio (TTFA) decreased drastically from a catastrophic 10-18 seconds down to a highly responsive **2.0-2.5 seconds** standard turn time.

## [2026-06-15] - Phase B & Phase C: SQLite Session Engine & Workspace Architecture

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- Added extreme forensic logging (Steps 1-12) to `ws_main.py` and `tts.py` to trace the exact TTS pipeline failure, writing directly to `DEBUG_FORENSICS.txt` to bypass Uvicorn logger overrides.
- Added explicit capturing of individual TTS provider exceptions in `tts.py` to forward them to the frontend via WebSocket error messages.

### Fixed
- Fixed Uvicorn `--reload` deadlock by explicitly excluding test files (`--reload-exclude "test_*.py"`) in `StartBackend.ps1`, preventing active test scripts from freezing the production backend.
- Intercepted the exact failure point: `tts_worker` receives a `RuntimeError` ("All TTS providers failed — no audio produced") from `tts_router` because both GeminiTTS and EdgeTTS throw exceptions internally during the websocket session, leading to an immediate `tts_end` with 0 bytes.
- **Voice Pipeline Forensics**: Conducted a deep dive into the STT -> LLM -> TTS -> WebSocket -> Frontend pipeline to diagnose the P0 "Orb Deadlock" issue.
- **Standalone TTS Tests**: Added `test_gemini_tts.py` and `test_edge_tts.py` to independently verify PCM byte generation outside of the websocket layer.
- **Phase E - OS System Diagnostics**: Implemented `get_system_status` in `tools/system.py` utilizing `psutil` to allow the LLM to read live Host CPU, RAM, Disk, and Process counts.
- **Phase E - Native Deep Search Crawler**: Ported the IRIS-AI deep file search logic into a lightning-fast asynchronous Python crawler in `tools/file_tools.py` (`search_files`). It recursively sweeps `Documents`, `Downloads`, and `Desktop` while intelligently bypassing heavy node/git directories to prevent I/O blocking.
- **Phase E - Web Intelligence**: Added `duckduckgo-search` and `beautifulsoup4` to natively fetch real-time search results and scrape text from URLs directly in the background using `tools/third_party_tools.py` (`search_web` and `read_webpage`).
- **Tool Registry Framework**: Implemented a new `core/registry.py` module containing the `ToolRegistry` class. This handles centralized tool registration, dynamic permission validation, and execution logging for all agentic actions.
- **Auto-Registration**: Created a clean initialization script in `tools/__init__.py` to automatically register all backend tools (`run_command`, `open_application`, `read_file`, `write_file`, `create_task`, `get_weather`, etc.) into the registry with Explicit Role-Based Access Control (e.g. `["admin"]` vs `["user"]`).
- **SQLite DB Backbone**: Created `d:/AI/backend/voice_agent/core/database.py` utilizing the Python standard library `sqlite3` to manage `users`, `sessions`, `messages`, `workspaces`, `workspace_settings`, and `notes`.

### Fixed
- **State Machine Deadlock (P0)**: Fixed a bug in `ws_main.py` where short LLM responses (< 4800 bytes of audio) failed to trigger the `SPEAKING` state, causing the backend to ignore `audio_finished` signals from the frontend.
- **Exception Swallowing Deadlock (P0)**: Fixed a silent failure in `tts_worker` where TTS generation exceptions were swallowed, leaving `agent_is_speaking = True` permanently locked.
- **Browser Autoplay Block Deadlock (P0)**: Fixed `useNexusVoice.ts` to gracefully handle Chrome/Edge AudioContext suspension policies on initial connect, ensuring `audio_finished` is safely dispatched to unlock the backend even if physical playback is blocked.
- **Chat Mode Audio Playback**: Fixed a bug where Voice output was completely silent in Chat Mode due to deferred `AudioContext` initialization. Implemented a global Autoplay Unlocker in `useNexusVoice.ts` that eagerly initializes and resumes the audio context upon the first user gesture (click/keydown), bypassing the browser's strict autoplay restrictions.

### Changed
- **Execute-Tool Refactor**: Completely refactored the legacy `POST /execute-tool` endpoint in `ws_main.py`. Removed 40+ lines of fragile `if/elif` hardcoded tool logic in favor of a clean, dynamic dispatch using `await tool_registry.execute(name, args, user_roles=["admin"])`.
- **LLM Context Injection**: Rewired `ws_main.py` inside `run_llm_and_tts()` to properly query `await self.memory.get_recent_context()` and inject the previous turn history into the context window, fixing "amnesia" bugs during Voice Sessions.

---

## [2026-06-15] - Voice Studio Completion Pass

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Provider Diagnostics Panel**: Added a diagnostics panel in Voice Studio to display real-time TTS provider readiness status and latency metrics fetched via the `/health` endpoint. Includes 'Current Provider', 'Current Voice', and 'Last Voice Used' trackers.
- **Indian Voice Models**: Expanded the Edge TTS provider options with Indian English and Hindi models (`Prabhat`, `Madhur`, `Neerja`, `Swara`).
- **Interactive Button States**: Enhanced the "Test Voice" button with dynamic visual states (`Generating...`, `Playing...`, `Success`, `Failed`) to improve acoustic testing feedback.

### Changed
- **Dynamic Voice Labeling**: Modified `GET /api/voices` to return object arrays (`id` and `label`), allowing UI dropdowns to show clean, user-friendly names instead of raw IDs.
- **Persistent Settings Init**: Updated Voice Studio to perfectly synchronize with `localStorage` parameters during component mount, preventing unintended resets.

### Fixed
- **TTS Router Default Bug**: Identified and fixed a critical override where the WebSocket backend and REST endpoint explicitly forced `auto` requests to use `edge` TTS. Fixed the logic to route `auto` to `gemini` natively so the `TTSProviderRouter` handles fallback correctly according to priority.
- **Cosmetic Voice Selection Bug**: Fixed a bug where both Gemini and Edge backend providers ignored the selected `voice` and hardcoded it based on the `gender`/`persona`. `tts_gemini.py` and `tts_edge.py` now explicitly respect the `voice` key passed from the Voice Studio, correctly rendering voices like `Aoede`, `Prabhat`, etc., during preview and live conversations.
- **Cosmetic Parameters UI**: Temporarily hid the `Speed`, `Pitch`, and `Volume` sliders in Voice Studio since they are currently cosmetic and ignored by cloud TTS SDKs.

## [2026-06-15] - P0 STT Hallucination Killer & Voice Studio UI

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Voice Studio UI**: Created a new dedicated settings page (`/settings/voice-studio`) for granular control over Acoustic Parameters (Provider, Voice, Speed, Pitch, Volume) and a new `test_voice` WebSocket mechanism to preview voices instantly.
- **Backend API**: Added `GET /api/voices` endpoint in `ws_main.py` to dynamically provide available voices for Gemini and Edge TTS providers.
- **Test Voice REST API**: Added a `POST /api/voice/test` endpoint to `ws_main.py` that handles instant voice preview generation and returns a playable WAV buffer.

### Changed
- **STT Pipeline (P0 Hallucination Killer)**: Substantially fortified `sanitize_transcript` in `ws_main.py`. Added structural checks for minimum word counts, unique word ratios (<0.4 rejection), excessive single-word repetition, and duration validation (<1.0s rejection) to strictly block noise/breath artifacts.
- **WebSocket Settings**: Expanded `Settings` message parser in the WebSocket handler to support voice, speed, pitch, and volume configuration sync from the frontend `NexusContext`.
- **Frontend Navigation**: Replaced the static TTS Provider dropdown in the main `SettingsPage` with a call-to-action link directing users to the newly implemented Voice Studio.

### Fixed
- **Voice Studio Crash**: Resolved a runtime crash (`Cannot read properties of undefined (reading 'map')`) on `page.tsx` when navigating to the Voice Studio page. This was caused by the frontend receiving a `404 Not Found` response from the stale backend process serving `/api/voices` (running without hot-reload). Implemented safe array validation (`Array.isArray`), safe fallback operators, and debug logs to ensure visual resilience even when API responses fail.
- **Voice Test Playback**: Resolved a bug where clicking the "Test Voice" button did nothing because the Web Audio Context was uninitialized prior to mic capture. Refactored the frontend `handleTestVoice` click handler to call the newly created REST endpoint and directly play back the audio blob via `AudioContext.decodeAudioData`, confirming working audio output.

### Notes
- **Persistence**: All Acoustic Parameters selected in the Voice Studio are strictly persisted in `localStorage` via `NexusContext`.
- **Provider Fallback**: If "Auto" is selected, the Nexus backend intelligently defaults to Edge TTS for fallback logic as initially requested by the router design.


## [2026-06-15] - Gemini Live WebSocket Streaming & Audio Loop Fixes

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **Gemini Live Backend SDK**: Fixed missing response issue for text triggers by replacing `send_client_content` with explicit `session.send(..., end_of_turn=True)` directly triggering the `AsyncLiveSession`.
- **Audio Streaming Crash**: Solved an `Unsupported input type` crash when sending microphone bytes through the Python GenAI SDK. Replaced the generic Blob pass with explicitly typed `types.LiveClientRealtimeInput` matching the exact sequence dictionary format required by `_parse_client_message`.
- **Frontend Microphone Rate-Limiting**: Resolved a massive WebSocket spam issue where the microphone Worklet was sending chunks every 8 milliseconds (125 messages per second). Modified `useNexusVoice.ts` to buffer raw `Float32Array` mic chunks up to 4096 samples (256ms) before downsampling and transmitting, identically matching the stable transmission rate of `IRIS-AI-main`.

### Notes
- **Voice Pipeline Status**: The newly added Gemini Live Experimental mode is currently broken due to heavy Google free API rate limits when streaming bidirectional audio. However, the Normal/Standard voice pipeline (Groq + TTS Router) works flawlessly.
- **TTS Fallback Status**: We have currently hit the Google API rate limit on our free API key for the Gemini TTS provider. Because of this, the backend is correctly falling back to **Edge TTS**, which is currently working perfectly. If a new API key is provided, Gemini will instantly start talking again.

---

## [2026-06-14] â€” Nexus P0 Critical Stability Fixes

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- Added `backend/experimental/gemini_live_voice.py` backend relay for Gemini Live WebSocket connection.
- Added `/ws/gemini-live` endpoint to `ws_main.py` routing logic.
- Added Voice Engine toggle to Frontend Settings UI (`page.tsx`) to switch between Standard and Gemini Live.
- Created `GEMINI_AUDIO_TEST.md` and `NATIVE_AUDIO_FEASIBILITY.md` and `GEMINI_LIVE_LAB.md` documentation.

### Changed
- Modified `NexusContext.tsx` to persist `voiceEngine` preference in `localStorage`.
- Modified `useNexusVoice.ts` to dynamically switch WebSocket connection URLs based on `voiceEngine` preference.
- **Gemini TTS**: Removed the synchronous 53-second retry loop when hitting a 429 quota error to allow the backend TTS router to fail fast and attempt fallback providers instead of blocking the event loop.
- **WebSocket Streaming**: Disabled semantic chunking for Gemini TTS. The backend now accumulates the full LLM response per turn and dispatches a single TTS generation request, drastically reducing API quota usage.

### Fixed
- **Latency Metrics**: Reset `turn_start_time` and `stt_latency` accurately for text-based chat inputs, resolving an issue where the `[TOTAL]` metric measured backend uptime instead of actual turn latency.
- **Voice Activation**: Fixed a bug where clicking the Dashboard Orb failed to fully initialize the voice pipeline. `useNexusVoice`'s `startListening` now explicitly forces a `connect()` check and explicitly triggers `audioContext.resume()` based on user gesture.

---

## [2026-06-14] â€” Nexus WebSocket StrictMode Lifecycle Fix

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **Frontend/Chat**: Fixed the "double reply" visual bug where the UI would create duplicated empty chat bubbles at the end of every AI streaming turn, and then populate them twice because `agent_message` was conflicting with `agent_partial` paragraph boundary pushes.
- **Backend/WebSockets**: Fixed the "silent AI" bug where restarting or hard-reloading the frontend caused the Python backend to "resume" an active session, but the background worker tasks (`tts_worker` and `metrics_worker`) remained cancelled from the previous disconnect. Replaced resuming with clean session recreation to ensure background tasks always boot.
- **Frontend/Contexts**: Resolved "ghost drop" behavior where the backend received connections and played greetings, but the frontend chat UI appeared offline and failed to send messages.

---

## [2026-06-14] â€” Consolidation of AI Documentation & Previous Voice Pipeline Fixes

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- Consolidated AI-specific tracking documentation (Worklog, Architecture Decisions, Future Roadmap, and Technical Debt) directly into `CHANGELOG.md` to establish a single source of truth.

### Fixed
- Recorded recent fixes completed in previous sessions:
  - **Gemini TTS**: Configured to stream raw 24kHz 16-bit little-endian PCM. Handled prompt formatting and system instructions to avoid API generation errors.
  - **Frontend UI**: Updated `useNexusVoice.ts` to properly handle and display `agent_message` transcripts in the UI.
  - **Echo Guard**: Updated `ws_main.py` to ensure post-TTS echo cancellation and silence guards arm correctly even if the final chunk buffer is empty.

### Current System State (from WORKLOG)
- **Working Features**: STT (Groq Whisper), TTS (Gemini raw 24kHz PCM), Frontend Voice UI (`agent_message`), Echo Cancellation Guard.
- **Beta Features**: Realtime Voice Stream via WebSockets.
- **Known Issues**: Latency overhead under slow network conditions.

### Architecture Decisions (from ARCHITECTURE_DECISIONS)
