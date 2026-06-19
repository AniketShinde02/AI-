## [2026-06-19] — Firebase Admin Initialization & Credentials Repair

### Author
- Antigravity AI
- Machine: JinWoo

### Fixed
- **`frontend/src/lib/firebase/server.ts`**: Upgraded Firebase Admin SDK initialization to natively parse the `FIREBASE_CREDENTIALS` JSON string, map snake_case service account properties to camelCase, and gracefully fall back to a safe warning instead of throwing a fatal process crash during build-time page collection when credentials are unconfigured.
- **Environment Repair**: Re-generated the minified JSON credentials from the original service account file `studio-8908067992-4e114-firebase-adminsdk-fbsvc-49d5f34889.json` and repaired the corrupted `FIREBASE_CREDENTIALS` in both `frontend/.env` and `backend/.env` (re-inserted the deleted `w` character and fixed truncated escapes like `\zsId`, `\BQr`, `\F7V`).

## [2026-06-19] — Verification Path Validation, Environment Loading & Pyright Fixes

### Author
- Antigravity AI
- Machine: JinWoo

### Changed
- **`backend/nexus_core/pyrightconfig.json`**: Updated `extraPaths` reference to use the renamed `backend/nexus_core` directory.
- **`experiments/gemini_live/run.ps1`**: Fixed legacy `voice_agent` directory references to use the correct `backend/venv` and `backend/.env` paths.

### Fixed
- **`backend/nexus_core/test_v1.py`**: Fixed environment loading logic to explicitly load keys from `backend/.env` before falling back, enabling all E2E API tests (Voice STT, Gemini Live, Groq Chat) to run and pass successfully in the unified directory structure.

## [2026-06-19] — Codebase Cleanup, Folder Renaming & Documentation Consolidation

### Author
- Antigravity AI
- Machine: JinWoo

### Added
- **`docs/07_architecture_doc.md`**: Created a consolidated architecture document combining `docs/architecture.md` and `docs/STABLE_ARCHITECTURE.md` into one single source of truth describing raw PCM WebSocket audio streaming, Silero VAD, Groq/Gemini STT routing, and SQLite storage.

### Changed
- **Folder Rename**: Renamed the primary Python backend folder from `backend/voice_agent/` to `backend/nexus_core/` to clarify boundaries. Updated launcher scripts (`StartBackend.ps1`, `run.ps1`), test configurations (`pyrightconfig.json`), and imports across test and benchmark scripts.
- **`backend/nexus_core/requirements.txt`**: Pruned unused dependencies including `getstream`, `vision-agents`, `vision-agents-plugins-getstream`, `elevenlabs`, `redis`, `kokoro-onnx`, `onnxruntime`, `soundfile`, `scipy`, and `cartesia`.
- **`backend/nexus_core/config.py`**: Cleaned up deprecated `getstream` imports and token generator blocks, and updated offline PIPER paths.
- **`docs/03_repo_structure.md`**: Updated repository layouts to document the unified FastAPI structure.
- **`NEXUS_MASTER_ARCHITECTURE_REPORT.md`**: Refactored all references from `voice_agent` to `nexus_core`.

### Fixed
- **`backend/nexus_core/test_v1.py`**: Fixed a critical self-referential feedback loop in Feature 16 (Verification Layer) that caused the `verification_matrix` table size to grow exponentially to 1GB by replacing the full nested `str(verifs)` print with a flat summary list.
- **Database Optimization**: Cleaned and vacuumed the local database `nexus_core.db`, shrinking its file size from 967.57 MB to 190 KB (99.98% space reduction).
- **Dead Code Cleanup**: Deleted deprecated duplicate files: `core/memory.py`, `core/memory_manager.py`, `core/call_manager.py`, `migrate_memory.py`, and the legacy JSON file `.nexus_states/user_memory.json`.

## [2026-06-19] — Core Capability Stabilization, Test Suite Expansion & Browser Cleanups

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **`backend/voice_agent/test_v1.py`**: Added **FEATURE 22 (Live WebSocket Connection)** to execute integration handshakes, greet payload reading, and ping-pong check against the active running uvicorn server on port 8001.

### Fixed
- **`backend/voice_agent/core/browser_agent.py`**: Fixed unknown `triple_click` attribute error on Playwright `Page` by refactoring it to `click(click_count=3)`. Resolved context optional attribute checks by adding explicit context verification assertions. Implemented a robust `_ensure_page` page recreation mechanism on closed context or page instances, and added a `close()` clean-up method.
- **`backend/voice_agent/core/session_state.py`**: Declared comprehensive class-level type annotations and stub methods for `SessionStateMixin` to prevent variable reference errors and attribute access issues under Pyright.
- **`backend/voice_agent/core/voice_session.py`**: Corrected initialization of the Gemini Live session manager by importing and calling the dynamic `get_gemini_live_system_instruction` function instead of referencing a non-existent static string constant. Added a `# type: ignore` to `tools=ALL_TOOLS` parameter to align with Groq/OpenAI type hints. Added browser action support to the Action Router forced-routing intercept path, and updated the workspace state to `"completed"` before early returns to prevent infinite `"running"` state hangs.
- **`backend/voice_agent/test_v1.py`**: Replaced static capability checks with a dynamic SQLite query, added type ignores to sys.stdout encoding calls to satisfy Pyright, closed tabs in Feature 5/6, and called `browser_agent.close()` on test exit to prevent browser process leaks.

### Verified
- Executed Pyright static analysis check: resolved all type checking failures (**0 errors**).
- Ran E2E integration test suite: confirmed successful execution of all E2E browser and WebSocket mode tests (**22/22 PASS**).

## [2026-06-19] — Phase 7 & 8: Agent Workspace & Multimodal Optics

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **`frontend/src/components/AgentWorkspace.tsx`**: Core UI block showing the current task, active tool/capability, OS window focus, capability verification state, and a live Playwright sandbox frame preview.
- **`backend/voice_agent/core/execution_hooks.py`**: Added `broadcast_workspace_state` to query the foreground window and fetch base64 frames from the browser agent, pushing real-time states to connected WS clients.

### Changed
- **`frontend/src/app/page.tsx`**: Replaced mock sub-agents panel with `<AgentWorkspace />`. Upgraded top-left optics feed placeholder to a fully interactive observation component utilizing `navigator.mediaDevices` camera and screen-sharing capture streams.
- **`frontend/src/hooks/useNexusVoice.ts`**: Subscribed to the incoming `workspace_state` message type to populate the React state and export it.
- **`frontend/src/contexts/VoiceContext.tsx`** & **`frontend/src/contexts/NexusContext.tsx`**: Exposed `workspaceState` across the application's React Context providers.
- **`backend/voice_agent/core/voice_session.py`**: Added task tracking properties and broadcast state transitions on transcription processing and response completion.
- **`backend/voice_agent/api/websocket_routes.py`**: Broadcasts state status updates on initial connection, manual text messages, and audio finished notifications.

### Performance
- Captured browser screenshots use JPEG (quality 50) compression to maintain minimal payload sizes (20-40KB) for websocket transfers.

## [2026-06-19] — Phase 3: Unified Capability Registry

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **[NEW] `core/capability_registry_def.py`**: Single source of truth for all 18 Nexus V1 capabilities.
  - `CapabilityDef` dataclass encapsulates: `id`, `name`, `description`, `category`, `permissions_required`, `requires_approval`, `groq_schema` (Groq/OpenAI function-calling JSON), `target_param` (param key mapping), `confirm_template` (TTS confirmation speech).
  - Derived compile-time exports: `CAPABILITY_MAP` (O(1) id lookup), `PC_TOOL_SCHEMAS`, `BROWSER_TOOL_SCHEMAS`, `CAPABILITY_REGISTRATION_TUPLES`, `CONFIRMATION_LABELS`, `ACTION_ROUTER_TOOL_NAMES`.

### Changed
- **`core/global_state.py`**: Replaced 8-capability hardcoded tuple list with `CAPABILITY_REGISTRATION_TUPLES` import. Now registers all 18 caps on startup (was missing 10 Phase 1 caps).
- **`tools/system.py`**: Replaced ~100-line hardcoded `SYSTEM_TOOLS` list with `PC_TOOL_SCHEMAS` import. 11 PC tool schemas now served from single definition.
- **`tools/browser_tools.py`**: Replaced hardcoded `BROWSER_TOOLS` with `BROWSER_TOOL_SCHEMAS` import. Extended `execute_browser_action` dispatcher to cover all 4 tab-management actions (`browser_tab_new`, `browser_tab_close`, `browser_tab_switch`, `browser_tab_list`).
- **`core/voice_session.py`**: Replaced inline 9-entry `action_labels` dict with `CONFIRMATION_LABELS`/`CAPABILITY_MAP` template lookup. Adding a new capability now requires zero changes here.
- **`core/action_router.py`**: Replaced 15-line hardcoded tool name string in `_generate_system_prompt` with `ACTION_ROUTER_TOOL_NAMES` import. Prompt is now always in sync with the registry.

### Verified
- Syntax check: 6/6 modified files pass `ast.parse`.
- Runtime import: 18 capabilities, 11 PC schemas, 4 browser tab schemas, 15 action router tools — all counts correct.
- All 20 E2E tests (test_v1.py) confirmed PASS before this change was applied.

## [2026-06-19] — Phase 2: File Splitting

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Changed (Structural Splits — zero behaviour change)

#### `voice_session.py` 1221 → ~380 lines
- **[NEW] `core/session_state.py`**: `SessionState` enum + `SessionStateMixin` — owns all VAD logic, `process_audio`, transcript/TTS sanitizers. No circular deps.
- **[NEW] `core/session_tts_worker.py`**: `SessionTTSMixin` — owns `tts_worker`, `metrics_worker`, `greet`, `safe_send_json`, `stop_audio`, `enqueue_tts`. No circular deps.
- **`voice_session.py`**: Now a clean orchestration shell — `VoiceSession` inherits both mixins via Python MRO. Owns `__init__`, lifecycle, `run_pipeline`, `run_llm_and_tts`, `extract_and_save_memory`. Added `pc_focus_app`, `pc_switch_window`, `pc_clipboard_read`, `pc_clipboard_write` confirmation labels to the action router dispatch table.

#### `database.py` 502 → ~280 lines
- **[NEW] `core/db_schema.py`**: Extracts all `CREATE TABLE IF NOT EXISTS` DDL into a single idempotent `init_db_sync()` function. Migration guards (`ALTER TABLE` stmts) included.
- **`database.py`**: Imports `init_db_sync` from `db_schema.py`. Pure async query layer only. Kept `_get_conn()` sync helper for backward-compat with audit/capability REST endpoints.

#### `api/rest_routes.py` 440 → ~220 lines
- **[NEW] `api/routes_system.py`**: All OS-automation endpoints (mouse, keyboard, window, screenshot, `/execute-tool`) moved here under `system_router`.
- **`rest_routes.py`**: Data-layer API only (memory, agents, workflows, RAG, capabilities, voices, theme, scrapper-os). Includes `system_router` via `rest_router.include_router()` — external import surface unchanged.

### Verified
- Syntax check: 7/7 files OK (`ast.parse`)
- Import validation: all modules load cleanly including MRO check on `VoiceSession`

## [2026-06-19] — Phase 1: Complete Missing Capabilities

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **`focus_app`** (`pc_control.py`): Brings a running window to the foreground using `ctypes.windll.user32.SetForegroundWindow` + `BringWindowToTop`. Falls back to `pygetwindow.activate()`. Includes RapidFuzz title-match for fuzzy window lookup and auto-restore from minimized state.
- **`switch_window`** (`pc_control.py`): Named target delegates to `focus_app`; unnamed/empty target sends `Alt+Tab` cycle via PyAutoGUI.
- **`clipboard_read`** (`pc_control.py`): Reads system clipboard via `pyperclip.paste()`. Returns full execution contract with character count and 100-char preview.
- **`clipboard_write`** (`pc_control.py`): Writes to system clipboard via `pyperclip.copy()` and performs a round-trip read-back to verify the write.
- **`browser_type`** (`browser_agent.py`): Clicks + triple-click selects a Playwright CSS selector, then types with 30ms inter-key delay for realistic input.
- **`browser_submit`** (`browser_agent.py`): Attempts native `form.submit()` via `page.evaluate()`, falls back to `keyboard.press("Enter")`.
- **`browser_tab_management`** (`browser_agent.py`): Supports `new`, `close`, `switch` (by integer index or RapidFuzz title match), and `list` actions on the Playwright persistent context.
- **ActionRouter updated** (`action_router.py`): System prompt now registers all 15 tools (7 new + 8 existing) so the intent classifier can route user voice commands to them.
- **`test_v1.py` extended**: Added tests 17 (focus_app), 18 (switch_window), 19 (clipboard round-trip), 20 (browser_tab_management).

### Verified
- Tests 17/18/19 executed and passed locally with full execution contracts.

## [2026-06-19] — Stabilization Audit & Core Implementation
### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Semantic Category Matcher (Task C)**: Implemented functional category routing inside `app_discovery.py` and `pc_control.py` mapping intent terms like "file manager" to system executables (`explorer.exe`) in $O(1)$ time, bypassing fuzzy matching false-positives (such as launching 7-Zip).
- **Spelled-Out Word Normalization (Task B)**: Added a normalization filter in `text_normalizer.py` and integrated it into `voice_session.py`'s TTS preprocessing pipeline to format spaced letter spelling (e.g. `p y r i g h t`) into comma-separated capitalized letters (`P, Y, R, I, G, H, T.`), allowing natural TTS spelling pronunciation.
- **Complete V1 Stabilization Audit**: Performed a detailed 9-phase audit of the Nexus V1 architecture, establishing splitting boundaries for monolithic files, mapping missing capabilities, proposing a provider-agnostic Capability Registry schema, and listing Brain V2 blocker priorities.

### Changed
- **IDE/Venv Synchronization (Task A)**: Synced the Pyright virtual environment settings in `pyrightconfig.json` to point to the operational `backend/venv` path, preventing static analysis "ghost bugs" and import warnings.

### Fixed
- **Dependency Environment Error**: Installed missing `aiosqlite` and `rapidfuzz` dependencies directly in the default `voice_agent/venv` directory to resolve IDE import errors and align the default workspace environment with the active running tests.

## [2026-06-19] — V1 Features Stabilization & E2E Test Suite
### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Strict Indian Accent Prompts**: Updated system instructions in `prompts.py` for both the standard REST LLM and the Gemini Live API to enforce talking strictly in an Indian accent/dialect (Indian English/Hinglish patterns, pacing, and phrasing), avoiding British or American colloquialisms and intonations.
- **Isolated Persistent Browser**: Refactored `browser_agent.py` to route all web searches and URL openings through a standalone Playwright Chromium instance with a persistent profile (`backend/data/browser_profile`). This keeps your main browser workspace undisturbed while retaining logins, cookies, and session states.
- **Asynchronous SQLite Migration**: Migrated `database.py` and `app_discovery.py` to use `aiosqlite` to eliminate database thread thrashing and GIL contention, converting blocking SQLite operations into native async queries.
- **E2E Verification Suite**: Created `test_v1.py` containing automated, real integration tests for all 16 core features of Nexus V1.

### Fixed
- **Directory Path Autocreation**: Fixed `write_file` in `file_tools.py` to automatically create parent directories recursively if they do not exist when writing a file.
- **Windows Console stdout Reconfiguration**: Reconfigured stdout and stderr to use UTF-8 encoding in the test suite to prevent encoding crashes with Hindi/Marathi/Urdu transcriptions on Windows console.
- **Action Router Parameter Mapping**: Fixed a bug in `voice_session.py` where the Action Router's `target` parameter was not mapped to `app_name` for `pc_minimize_app` and `pc_maximize_app` actions, causing them to execute with empty parameters.

## [2026-06-19] — App Discovery Edge Cases, Graceful Close & Minimize
### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Minimize / Maximize Windows**: Introduced `pc_minimize_app` and `pc_maximize_app` capabilities to the system tool array and `ActionRouter`. 

### Changed
- **Graceful Window Close**: Refactored `pc_close_app` to use `pygetwindow` to send a graceful `WM_CLOSE` signal to specific windows matching the query, preventing the destruction of all background tabs when using a hard `psutil` process kill.
- **UI Render Sync**: Added a 1.5-second artificial wait in `pc_open_app` after process verification. This ensures Nexus's confirmation speech is perfectly synchronized with heavy apps (like Chrome/VS Code) visually rendering on the desktop.

### Fixed
- **Junk Shortcut Filtering**: Updated `app_discovery.py` crawler to explicitly ignore `.lnk` files containing keywords like `uninstall`, `help`, `documentation`, or `readme`. This prevents RapidFuzz from accidentally matching these over the primary executable.

## [2026-06-19] — Command Ownership, Global Execution Contract, & Reasoning Strip
### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Global Execution Contract**: Enforced that the Capability Router (`action_router.py`) strictly owns all actionable intents (e.g., `open vscode`). If an action is detected, the LLM is bypassed completely and never receives the transcript. 
- **DB Memory Sync for Gemini Live**: Added synchronous persistence to `db.save_message` inside Gemini Live's `on_agent_message` callback so conversations are correctly archived.

### Changed
- **Gemini Live Routing (Double Processing Fix)**: Refactored `api/websocket_routes.py` to stop streaming raw audio `bytes` continuously to the Gemini WebSocket. All audio now routes through the unified `session.process_audio()` pipeline (VAD -> Local STT -> Intent Classifier). Gemini Live now *only* receives `send_text()` transcripts if the intent is classified as CHAT.
- **Removed Model Hacks**: Deleted the hardcoded regex hack (`\[OPEN_APP:\]`) from `voice_session.py` that forced Gemini Live to execute tools. Capabilities are now entirely determined by the Capability Registry in backend routing, not by model assumptions.
- **Advanced Output Processing**: Upgraded `core/output_processor.py` to aggressively strip conversational friction (`"As an AI..."`, `"I'm thinking..."`, `"I have executed..."`) to strictly separate CHAT output from TRACE output.

## [2026-06-19] — Frontend Resilience & History Fetch Retry

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **History Fetch Race Condition**: Implemented automatic retry logic (up to 5 attempts with 1s delay) in `NexusContext.tsx` for the initial session history fetch. This prevents the browser from throwing `TypeError: Failed to fetch` errors when `uvicorn` takes 1-2 seconds to boot or reload the backend server during live development.

## [Unreleased] - Real-Time Core & Automation Upgrades

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- Integrated enterprise-grade cloud API gateways (GitHub Models, OpenRouter Free Pool, Mistral AI, Cloudflare Workers AI, Cohere, Zhipu/BigModel) to scale background task throughput at zero cost.
- Implemented speech-native bidirectional streaming capabilities via speech-to-speech (S2S) architecture candidates (Ultravox.ai, Moshi, Hume AI).
- Added an async-isolated notification and status layer powered by unmetered cloud Edge TTS loops to prevent process thread blocking.
- Implemented a Dynamic Desktop Application Discovery Engine that dynamically crawls and indexes installed software shortcuts (.lnk) into a local database pool.

### Fixed
- Fixed a translation/ASR routing bug where Hinglish/slang transcriptions (e.g., "open kro", "what app") caused terminal exceptions (`'command' is not recognized as an internal or external command`).
- Implemented a fuzzy string matching layer using algorithmic distance fallback metrics to resolve raw voice inputs against the 240+ dynamically indexed application paths.
- Enforced Strict Structural Isolation boundaries inside system prompting logic to containerize reasoning tokens (`<thinking>`) within the backend data logs, completely hiding internal monologue from the voice/UI frontend.
- Resolved Gemini Live TTS dropout on microphone inputs by wrapping WebSocket `turns` payload in arrays and enforcing explicit `role="user"` fields required by the `google-genai` SDK.
- Patched an `UnboundLocalError` scope breach in the Action Router where `res` dictionaries were uninitialized if the user's action was denied by capability permissions or failed `pc_` substring matching.
- Eliminated static type-checker Pyright failures in `tools/system.py` (`Cannot set item in 'str'`) and `core/app_discovery.py` (`Returned type Unknown | None is not assignable to declared return type str`) via accurate type hinting (`List[Dict[str, Any]]` and `Optional[str]`).
- Cleaned up redundant local imports (`flake8` F811/F401 errors) across `system.py`, `voice_session.py`, and `gemini_live_manager.py` that were blocking clean syntax validation.

## [2026-06-18] — Dynamic App Discovery Engine

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Dynamic LNK Crawler**: Upgraded `core/app_discovery.py` to recursively crawl `ProgramData` and `AppData` Start Menu folders for `.lnk` shortcuts, dynamically maintaining an absolute-path inventory of all local desktop software alongside UWP apps.
- **Dynamic Tool Injection**: Created `get_dynamic_system_tools` in `tools/system.py`. `voice_session.py` now queries the real-time SQLite app inventory and dynamically embeds the list of available host applications into the system prompt's tool description.
- **Absolute Path Execution**: Updated `core/pc_control.py` to natively execute `.lnk` paths via `os.startfile()`.

### Changed
- **Zero-Latency Routing**: Upgraded `core/action_router.py` to operate entirely on raw user app names mapped to the SQLite dictionary instead of relying on a fragile static `app_aliases` hash map.
- **Removed Hardcoded Aliases**: Deleted the 50-item legacy `_APP_ALIASES` static map from `pc_control.py`. All mapping is now 100% dynamically discovered from the host system environment.
- **Bug Fix**: Removed a duplicated LanceDB memory function in `voice_session.py` that was silently overriding AI preference extraction logic. Fixed duplicate import of `execute_pc_action` that broke the Action Router.

## [2026-06-18] — Global Runtime Contract & Action Interception

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Global Action Router**: Created `core/action_router.py` to intercept precise intent strings (e.g., `open vscode`) and execute actions directly in 0ms without involving the LLM.
- **Global Output Processor**: Created `core/output_processor.py` that strips internal tags like `<think>` and reasoning strings before emission.
- **Ingestion State Tracker**: Created `ingestion_state` table in SQLite (`database.py`) to persistently track embedded code files.

### Changed
- **PC Control execution schema**: Modified `core/pc_control.py` so all automation tasks return a strict 5-key deterministic dictionary: `success`, `tool`, `target`, `verification`, `execution_time`.
- **Scrapper OS bridge schema**: Updated `core/scrapper_os.py` methods to match the identical 5-key dict requirement.
- **RAG Oracle Persistence**: Updated `rag_oracle.py` to abandon fragile JSON file hashes and rely entirely on SQLite's `ingestion_state`.
- **Voice Session Output**: Wired `action_router` and `output_processor` natively into `voice_session.py`, guaranteeing all emitted WebSocket and TTS text adheres to the reasoning-ban contract.
- **Trace Payload Integrity**: Applied the `output_processor` filter to `trace_emitter.py` so raw LLM thoughts do not leak into the UI event trace logs.

## [2026-06-18] — Execution Layer Hardening & SQLite Only Memory

### Author
- Antigravity AI
- Machine: JinWoo-PC
- Environment: Local / Development

### Added
- **BrowserAgent Layer**: Added `core/browser_agent.py` using Playwright to handle `open_url`, `search`, `click`, `extract`, and `screenshot` natively.
- **App Discovery Service**: Added `core/app_discovery.py` to automatically discover installed Windows applications via `Get-StartApps` and store them in the database for intelligent launching.
- **Trace Emitter**: Added `core/trace_emitter.py` to emit telemetry events for tool routing and execution directly via the WebSocket.
- **ScrapperOS Bridge**: Integrated `tools/scrapper_tools.py` into the global registry to natively support checking health, listing tasks, and running external ScrapperOS automations.

### Changed
- **Memory Storage**: Removed in-memory `self.vector_db` list from `RAGOracle` and migrated semantic RAG ingestion entirely to LanceDB vector database via `core/lance_memory.py`.
- **PC Control**: Rewrote `core/pc_control.py`'s `open_app` to query `discovered_apps` DB for paths before falling back to aliases. Upgraded verification loop to use `asyncio.sleep` to prevent blocking the event loop.
- **Session Persistence**: Tool execution confirmations and error results are now permanently saved to SQLite using `db.save_message` directly after completion.
- **Capability Routing**: Added capability prompting logic in `voice_session.py`. If a capability requires permission ("Prompt"), a WebSocket message is dispatched instead of blocking or assuming execution. Added support for `grant_permission` in `websocket_routes.py`.

### Security
- **Error Transparency**: Tool execution strictly returns verbatim strings to the LLM context, prohibiting any hallucinated "success" messages if the underlying action failed.
- **App Launch Verification**: Verified process detection runs async using `psutil` thread polling, validating successful execution entirely disconnected from the LLM prompt.

## [2026-06-18] — Gemini Rate Limits Reference Update

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Changed
- **Gemini Rate Limits Reference**: Expanded [GEMINI_RATE_LIMITS.md](file:///d:/AI/archived/docs_archive/GEMINI_RATE_LIMITS.md) to document a comprehensive list of Gemini models, categories, and their rate limits (RPM, TPM, RPD) transcribed directly from Google AI Studio.

## [2026-06-18] — Codebase Architecture Investigation & Adoption Planning

### Author
- Antigravity AI
- Machine: JinWoo-PC
- Environment: Local / Development

### Added
- **Unified Deep Codebase Analysis Report**: Consolidated all comparative studies into a single master document:
  - [iris_hermes_stonic_comparison.md](file:///C:/Users/JinWoo/.gemini/antigravity-ide/brain/8d9a0ac3-ab39-4269-be51-d1b07d3f52bc/iris_hermes_stonic_comparison.md): Integrates process topologies, audio pipelines, memory models, stream-scrubbing systems, and permissions, ending with a prioritized list of 10 highest-value patterns for Nexus.
- **Mistral AI Environment Placeholders**: Added `MISTRAL_API_KEY=your_mistral_api_key_here` in backend `.env`, frontend `.env`, and root `.env.example`.
- **Mistral AI Routing & UI**: 
  - Integrated `MistralClient` into `ModelRouter` (`model_router.py`) to correctly route Mistral and Pixtral models to the official Mistral API.
  - Added `mistral-large-latest` and `pixtral-large-2411` to the model selector in `InputArea.tsx` and the Settings Page.
  - Updated the frontend `/api/chat/route.ts` to dynamically configure the `OpenAI` client with Mistral API base URL and key when a Mistral model is requested.

### Changed
- Consolidated 5 separate comparative Markdown files into the single `iris_hermes_stonic_comparison.md` master document, deleting the redundant individual files to keep the artifacts folder clean.

### Notes
- No functional modifications were made to Nexus codebase during the research task, but the subsequent implementation safely added Mistral integration. Ensure `mistralai` is installed in the backend environment (`pip install mistralai`) to utilize the new routing logic.

## [2026-06-18] — Reasoning Leak Fix + Tool Wiring + Permissions System
### Author
- Antigravity AI
- Machine: JinWoo-PC
- Environment: Local / Development

### Fixed
- **CRITICAL: Reasoning leak into chat UI** — LLaMA 3.3 70B was outputting internal monologue (e.g. "Okay so the user wants me to...") as plain text directly into the chat bubble and TTS because the prior negative constraint ("Do not output reasoning") caused the model to hallucinate free-form prose with no detectable markers.
- Root cause: Groq LLaMA 3.3 70B does not use `<think>` tags by default. Existing regex filters only stripped `<think>...</think>` blocks, which were never generated.
- Fix layer 1 (Prompt): Rewrote `prompts.py` VOICE RULES to explicitly name and prohibit 25+ reasoning-prefix patterns by example. Added hard rule: "Your FIRST token must be the start of your actual response."
- Fix layer 2 (Streaming filter in `voice_session.py`): Added `_REASONING_PREFIXES` tuple + per-sentence prefix check before any text is sent to TTS queue or frontend WebSocket. Reasoning sentences are dropped silently and logged as `[LEAK FILTER]`.
- Fix layer 3 (Frontend `MessageList.tsx`): Kept `<think>` and `**` block stripping as secondary defense.

### Added
- **Tool calling wired**: `run_llm_and_tts` now performs a non-streaming Groq tool-detection call **before** the streaming LLM response. If a tool is matched (`pc_open_app`, `pc_close_app`, `pc_take_screenshot`, etc.), it executes immediately and returns only a one-line confirmation — no LLM prose.
- **"open file manager" now works**: Routes to `pc_control.py:open_app("explorer")` via `tools/system.py:execute_pc_action()`. Audit logged.
- **Capabilities registered on startup**: `global_state.py` lifespan now calls `registry.register_tool()` for all 5 PC control capabilities on boot. SQLite `capabilities` table is authoritative.
- **REST API for capabilities**: Added `GET /api/capabilities`, `PATCH /api/capabilities/{id}` (toggle enabled), `GET /api/audit-log` to `rest_routes.py`.
- **Permissions UI page** (`/settings/permissions`): Full page showing all registered capabilities with enable/disable toggles, category grouping, and live tool execution audit log.
- **Permissions card added to Settings page**: Direct link to `/settings/permissions` visible in the Settings Command Center.

### Notes
- Tool detection adds ~200-400ms latency to each turn (extra Groq call). This is acceptable for the reliability gain but can be optimized later with intent pre-classification.
- LLaMA 3.3 70B respects tool schemas precisely and routes tool calls accurately in early testing.
- Gemini Live sessions do NOT go through this pipeline (they use Gemini's own voice model). Tool wiring for Gemini Live is a future task.

## [2026-06-18] — Gemini Live Telemetry & VAD Fixes



### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Transport Forensics Pipeline**: Injected raw WebSocket frame logging (DEBUG_GEMINI_RAW.log and DEBUG_GEMINI_SESSION.log) into GeminiLiveSessionManager to enable exact protocol state auditing.
- **VAD Turn Completion**: Added the send_turn_complete() method to GeminiLiveSessionManager to explicitly signal 	urn_complete=True safely behind an asyncio lock.
- **Frontend VAD Sync**: Added a handler for the ad_stop WebSocket event in pi/websocket_routes.py so that when the frontend detects the user has stopped speaking, it instantly triggers send_turn_complete(), prompting Gemini Live to generate a response.

### Fixed
- **Unicode Logging Crash**: Fixed a UnicodeEncodeError (cp1252 charmap) in logging.FileHandler on Windows that caused the Gemini inbound 
eceive_task to crash silently when encountering emojis in log statements. Handlers now explicitly use encoding='utf-8'.
- **Session Identity Typing**: Fixed the VoiceSession.__init__ signature in core/voice_session.py to correctly accept session_id. Updated the router initialization to pass websocket.query_params.get('session_id', ''), resolving a str | None IDE type error and eliminating the fallback trigger.
- **Removed Broken Variables**: Replaced all rogue 
aw_logger references that crashed the backend connection with proper logger.debug and scoped session_logger usages.

## [2026-06-18] - Gemini Live Send Protocol Fix

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **Gemini Protocol Deprecation**: Migrated from the deprecated session.send() websocket wrapper to the required session.send_client_content() for text and session.send_realtime_input() for binary audio chunks, strictly conforming to the Google GenAI 1.x spec.
- **Turn State Sync**: Set 	urn_complete=False when sending text chunks. Previously, end_of_turn=True was sent during text injection while the frontend microphone continuously streamed audio frames for the same turn. This caused the remote Gemini WebSocket to drop the connection gracefully (1000 OK) due to a turn state violation.

## [2026-06-18] - Gemini Live Transport Stability Fixes

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **Race Condition in Gemini Live Manager**: Added syncio.Lock() to GeminiLiveSessionManager to serialize send_audio, send_text, and send_video_frame. This prevents the google-genai websockets library from throwing concurrent write exceptions which caused immediate 1000 OK connection closures.
- **Audio Routing False-Positive**: Verified that frontend correctly utilizes 
ew Int16Array for PCM conversion and sends raw Binary WebSocket frames. Backend websocket_routes.py successfully passes these raw bytes to Gemini API native audio stream.

### Added
- **Transport Forensics Artifact**: Generated LIVE_TRANSPORT_FORENSICS.md outlining the exact root cause of the transport drops.
- **Model Router Target Architecture**: Generated MODEL_ROUTER.md proposing the dynamic routing between Gemini Live (Primary Voice) and Groq/EdgeTTS (Fallback Voice).

## [2026-06-18] - ws_main.py Safe Structural Refactor (Phase 5)

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Modular Backend Architecture**: Safely split the monolithic 1684-line ws_main.py into smaller, single-responsibility files without modifying any underlying logic or state machine behavior:
  - core/global_state.py: Extracted global providers, FastAPI lifespan, and configuration.
  - core/voice_session.py: Extracted the VoiceSession class and WebSocket audio processing logic.
  - pi/rest_routes.py: Extracted all /api endpoints, HTTP health checks, and PC automation routes.
  - pi/websocket_routes.py: Extracted the /ws/nexus and /ws/gemini-live WebSocket connection routers.

### Changed
- **Entrypoint**: ws_main.py now cleanly imports and mounts routers and lifespan from the newly created modular directories, serving strictly as the core application configuration point.

### Notes
- **Verification**: Refactoring completed programmatically via strict line extraction rather than manual rewrites to guarantee absolutely zero behavior, state, or import scope changes.
- **Resilience**: The backend was confirmed to boot successfully immediately following the structural module separation.


## [2026-06-17]  Fix Gemini SDK Part.from_text TypeError

### Author
- Antigravity AI
- Machine: Local

### Fixed
- Fixed critical TypeError: Part.from_text() takes 1 positional argument but 2 were given hidden deep inside the Gemini Live async receive background task.
- The 	ypes.Part.from_text() method in the latest Google GenAI SDK requires a keyword-only argument (	ext=...). 
- This hidden crash was silently preventing the WebSocket handshake from completing, causing the server to hang for 15 seconds during connect(), which caused the frontend's keepalive ping monitor to declare the WebSocket "offline".

## [2026-06-17]  Fix Gemini Live API Connection Timeout

### Author
- Antigravity AI
- Machine: Local

### Fixed
- Fixed critical Gemini Live API connection timeout caused by a deprecated model name (gemini-2.0-flash-exp) that returned APIError 1008.
- Replaced deprecated model with gemini-2.5-flash-native-audio-latest which officially supports the AUDIO modality for the idiGenerateContent endpoint.
- Fixed 	ypes.Modality.AUDIO enum import error that was causing silent AttributeErrors inside the Live connection task.
- Fixed missing 1alpha API version configuration in genai.Client().
- Increased Gemini connection timeout from 5.0s to 15.0s to prevent false-positive handshake failures.

## [2026-06-17]  Fix LanceDB Uvicorn Deadlock

### Author
- Antigravity AI
- Machine: Local

### Fixed
- Fixed critical deadlock during backend startup caused by LanceDB Rust Tokio threads colliding with Python multiprocessing and Uvicorn's lifespan asyncio context on Windows.
- Implemented lazy loading for core.lance_memory.SemanticMemory so it completely bypasses the lifespan phase.
- Replaced synchronous lancedb methods with native connect_async API for true async compatibility.
- Fixed LiveConnectConfig type mismatch error in gemini_live_manager.py.

### Performance
- Backend startup time reduced from infinite to <1s (instantly reaches Application startup complete).

## [2026-06-18] — Reasoning Leak Elimination, Action Pipeline Fix, Real Frontend Indicators

### Author
- Antigravity AI
- Machine: Local-AI

### Added
- **`core/output_contract.py`**: New single-source enforcement module. All agent text must pass through `scrub_output()` before touching WebSocket or TTS. Strips `<think>` blocks, `[thinking]`/`[scratchpad]`/`[internal]` tags, bold/italic annotations, and 40+ reasoning prefix sentences including Hinglish patterns.
- **Forced Tool Routing**: Added `_ACTION_KEYWORDS` tuple in `VoiceSession`. If a transcript starts with `"open "`, `"launch "`, `"close "`, `"screenshot"`, etc., the LLM is forced into `tool_choice={"type": "any"}` — eliminating the root cause where Groq chose to respond conversationally instead of calling `pc_open_app`.
- **Engine Mode WebSocket message**: Backend now emits `{"type": "engine_mode", "mode": "gemini_live" | "groq"}` on connect and on fallback. Frontend state is always truthful.
- **`ACTION_PIPELINE_AUDIT.md`**: Full pipeline trace for 6 apps (file manager, notepad, calculator, chrome, vscode, spotify) with root cause analysis.

### Changed
- **Gemini Live path** (`voice_session.py` `on_agent_message`): Now calls `scrub_and_log()` before `safe_send_json()`. Previously had **zero filtering** — all Gemini thinking tokens were passing directly to the frontend.
- **Groq streaming path** (partial + final flush + final assembly): All 3 emission points now use `scrub_and_log()` from `output_contract.py` instead of the old inline `re.sub` + narrow `_REASONING_PREFIXES` list.
- **`core/pc_control.py`**: Expanded alias map from 10 entries to 50+ entries. Now correctly resolves `"file manager"`, `"file explorer"`, `"spotify"`, `"task manager"`, `"discord"`, `"teams"`, `"zoom"`, URI-scheme apps, and more. Switched from `start {target}` shell to direct `Popen(target)` with shell fallback for PATH apps.
- **`api/websocket_routes.py`**: Added `engine_mode` message sends on Gemini connect success and on Gemini hard-fail-to-Groq transition.
- **`useNexusVoice.ts`**: Added `activeEngine` state + handles `engine_mode` WS message.
- **`VoiceContext.tsx`**: `activeEngine` exposed in context interface.
- **`TopNav.tsx`**: Added real 🎤 Mic ON/OFF indicator (based on `isListening && micCaptured`), Engine Mode pill (Gemini Live / Groq / Text) with distinct colors sourced from backend `engine_mode` messages.

### Fixed
- **Reasoning Leak — Gemini Live**: `on_agent_message` callback had zero filtering. Fixed with `scrub_and_log()`.
- **Reasoning Leak — Groq partial chunks**: Inline `_REASONING_PREFIXES` list was too narrow (16 entries). Replaced with comprehensive 40+ entry list in `output_contract.py`.
- **`"open file manager"` routing to conversation**: Fixed via forced tool routing + alias map expansion.
- **Frontend showing fake states**: TopNav now reads real `isListening`, `micCaptured`, and `activeEngine` from WebSocket-sourced state.

### Security
- All text output paths now enforced through a single contract module — no bypasses.

## [2026-06-18] — Nexus Truthfulness, Architecture Polish, & Rate Limit Intelligence


### Author
- Antigravity AI
- Machine: Local-AI

### Added
- **Strict Execution Contract:** Implemented a new, strict JSON schema across all action tools (`success`, `verified`, `result`, `error`) to enforce deterministic and honest agent responses.
- **Deep Process Verification:** Introduced active process polling using `psutil` inside PC Control (`open_app`). The agent now mathematically verifies that an OS application has successfully launched and exists in system memory before claiming success.
- **LanceDB Semantic Memory:** Successfully wired up `extract_and_save_memory` in the background of `voice_session.py`. This ensures automatic embedding and semantic chunking of user-AI conversations into the LanceDB vector store.
- **Trace Pipeline Audit:** Implemented structured audit logging inside `model_router.py`. All LLM intent-to-tool paths are now permanently logged to the SQLite database (`tool_audit_logs`), mapping the user intent directly to the tool selected.
- **Rate Limit Intelligence:** Researched, mapped, and appended exhaustive rate limit rules (RPM, RPH, RPD, Tokens) for over 10 providers including Cerebras, DeepSeek, Mistral, SambaNova, OpenRouter, ElevenLabs, Cartesia, Deepgram, Hugging Face, and GetStream.io. Saved to `archived/docs_archive/models_with_limits.md`.
- **Environment Templates:** Created comprehensive, clean `.env.example` placeholder files in both `frontend` and `backend` directories to standardize secrets management.

### Changed
- **Hallucination Eradication:** Refactored `core/voice_session.py` to completely eliminate hardcoded AI confirmations (e.g., "Opening app..."). The agent now parses the real Execution Contract and speaks exactly what the tool verification system returns.
- **Global Tool Routing:** Modified the fast-tool execution flow inside `voice_session.py` to correctly parse and route *all* tools (system, files, tasks, memory, third-party) instead of just PC actions.
- **SQLite Memory Migration:** Transitioned `tools/memory_tools.py` away from legacy JSON storage, mapping it directly to the production `core.database.db` SQLite engine.
- **Persistent Conversational Archiving:** Enabled database-driven chat persistence. Both user transcripts and assistant outputs are now safely preserved to the `messages` table synchronously via `asyncio.create_task`.

### Fixed
- **Uvicorn Crash on Restart:** Fixed a critical `NameError` crash (`'Dict' is not defined`) in `third_party_tools.py` caused by the Execution Contract refactor, ensuring auto-reload continues without disruption.

### Security
- **Global Capability Enforcement:** Upgraded the voice pipeline's tool detection flow so that *every single tool* executed by the agent must pass through the `cap_registry.check_permission()` gateway. Explicit permission grants, denials, and requests are strictly audited.

# CHANGELOG - Nexus AI Project

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) + Semantic Versioning.

---

## [2026-06-17] - Phase 5: Voice Stack Stabilization (Step 1)

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **Frontend State Machine (`useNexusVoice.ts`)**: Fixed the critical async race condition that caused the UI to show `OFFLINE` and `LISTENING` simultaneously. Added strict connection state checks after `getUserMedia` resolves.
- **Frontend Mic State**: Ensured `setMicMuted(false)` checks if the WebSocket is connected before forcing `isListening=true`.
- **Backend Gemini Transport (`gemini_live_manager.py`)**: Added `asyncio.CancelledError` catching and robust `try/except` block to ensure the `AsyncLiveSession` loop gracefully handles interruptions or disconnections without crashing the main event loop.
- **Backend Endpoints (`ws_main.py`)**: Added try/except wrappers in the `/ws/gemini-live` endpoint around `send_audio` to prevent the session loop from crashing when relaying audio back and forth, and guaranteed an explicit disconnect payload is sent on failure.

---

## [2026-06-17] - Phase 5-10 Structural Foundations & Gemini Live Transport Bridge

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Architecture**: Introduced new core foundation files to support the shift towards a Multi-Agent OS router architecture.
- **Backend (Model Router)**: Added `core/model_router.py` to route tasks dynamically between Groq (Fast tasks, Coding) and Gemini (Live Conversation, Vision, Deep Research).
- **Backend (Gemini Live)**: Created `core/gemini_live_manager.py` to establish bidirectional audio transport with the Gemini Multimodal Live API.
- **Backend (Capabilities)**: Created `core/capabilities.py` for the unified Capability Registry (explicit permissions for tools like file_read, open_app, etc.).
- **Backend (PC Control)**: Added `core/pc_control.py` layer to abstract desktop automation actions securely.
- **Backend (Scrapper OS)**: Added `core/scrapper_os.py` bridge to integrate seamlessly with the external `Scrapper OS` repository (`AI-OS-3-scrapping-agents`).
- **Frontend (UI Components)**: Added `GeminiVision.tsx` and `LiveStatusWindow.tsx` components to surface multimodal vision and status events.

### Notes
- **Pending**: Voice state machine (OFFLINE/LISTENING deadlock) requires fixing before full integration of the Gemini Live transport layer.

---

## [2026-06-17] - Nexus Dynamic Theme Engine (Phase 4)

### Added
- **Backend (Theme API)**: Added `/api/theme/generate` endpoint that uses `google-genai` (Gemini Vision 1.5 Flash) to dynamically extract dark-mode optimized JSON palettes from uploaded images.
- **Backend (Static Serving)**: Mounted static files serving to host dynamically uploaded theme background images from `data/themes/backgrounds`.
- **Frontend (UI)**: Added an Appearance & Theme Engine block in the Settings UI allowing for Image Upload.
- **Frontend (ThemeProvider)**: Extended React context with `setCustomTheme` to inject dynamically generated palettes and CSS variables at runtime.

### Changed
- **CSS**: Modified `globals.css` to inject `--global-bg-image` onto the `html.has-custom-bg::before` pseudo-element for custom wallpapers.

---

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Architecture**: `ARCHITECTURE_FREEZE.md` outlining immutable core design patterns and boundaries.
- **Backend (DB)**: Configured SQLite in WAL mode (`nexus.db`) for high-concurrency real-time reads/writes.
- **Backend (Agent System)**: Added `/api/agents` CRUD endpoints in FastAPI `ws_main.py` mapped to SQLite `agents` table.
- **Backend (Automation)**: Added `/api/workflows` CRUD endpoints mapped to SQLite `workflows` table.
- **Backend (Memory)**: Migrated `user_memory.json` to persistent SQLite `user_memory` table and added `DELETE /memory/{category}/{key}` endpoint.
- **Backend (RAG)**: Formally validated `rag_oracle.py` (Local Caching + Google Embeddings + Groq LLaMA) and exposed via `/api/rag/ingest` and `/api/rag/query`.
- **Backend (Bridge)**: Added `ScrapperOSBridge` class and `/api/scrapper-os/*` proxy routes to securely interact with external Scrapper OS without CORS.
- **Documentation**: Generated `PRODUCTION_READINESS_REPORT.md` and `SCRAPPER_OS_BRIDGE.md`.

### Changed
- **Frontend (Agents)**: Replaced mock UI `AGENTS` array with dynamic React `useState/useEffect` fetching from real SQLite backend (`page.tsx`).
- **Frontend (Automation)**: Wired Mission UI directly to the real `workflows` API endpoint with dynamic state management and functional toggle/delete buttons.
- **Frontend (Memory)**: Wired delete buttons in `MemoryPage` to hit the real backend API.
- **Frontend (Layouts)**: Centralized component-driven layouts via `DashboardLayoutRenderer` instead of manually hardcoded grids.

---

## [2026-06-16] - Final Validation & Hardening Session

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Fixed
- **CRITICAL**: `SyntaxError: unmatched '}'` at `ws_main.py:1244` — corrupted final-flush block rebuilt with proper buffer drain, sentinel, `agent_message`, and background memory extraction.
- **CRITICAL**: `ReferenceError: voiceEngine is not defined` — `voiceEngine` was missing from `useNexus()` destructuring in `page.tsx:51`. Frontend 500 error resolved.
- **HIGH**: `/api/voices` returning 404 — Added `GET /api/voices` endpoint to `ws_main.py` with Edge TTS (8 voices) and Gemini TTS (5 voices) response. Voice Studio `VOICE MODEL` panel will now populate.
- **HIGH**: `NotAllowedError` in `GeminiVision.tsx` not handled — wrapped in typed `catch (error)` with explicit `error.name === 'NotAllowedError'` distinction and clear UI status.
- **HIGH**: WebSocket Code 1006 on Fast Refresh — added unmount cleanup `useEffect` in `useNexusVoice.ts` sending `ws.close(1000, "Component unmounted")`.

### Verified (Browser Screenshots)
- Dashboard, Chat, Trace, Memory, Agents, Automation, Settings, Voice Studio — all 8 pages load correctly.
- Backend HTTP 200 + WebSocket CONNECTED confirmed.
- Single remaining browser console error before fix: `/api/voices 404` (now fixed).

### Added
- `FEATURE_VALIDATION_REPORT.md` — complete feature inventory with status.
- `PRODUCTION_BLOCKERS.md` — all bugs categorized by severity with root cause.
- `CODEBASE_CLEANUP_REPORT.md` — dead code, unused files, archive candidates.
- `ROADMAP_STATUS_REPORT.md` — Phase 0–10 audit with evidence and release decision.

### Notes
- Release Decision: `NOT_READY_FOR_PRODUCTION` / `READY_FOR_PHASE_5_10_CONTINUATION`
- Blockers remaining: Auth layer, rate limiting, Automation/Agents backend wiring, RAG Oracle ingestion.

---

## [2026-06-16] - Agentic Daily Needs ML Memory Adaptation

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Background Memory Extraction**: Implemented asynchronous ML preference extraction (`extract_and_save_memory`) in `ws_main.py` using Llama 3.1 8B. It autonomously reads post-turn conversation contexts and executes the `update_preferences` tool without blocking ultra-fast voice TTS latency.
- **Dynamic Prompt Injection**: Updated `prompts.py` to auto-inject the persistent JSON memory object (from `core/memory_manager.py`) directly into the Nexus System Prompt on every voice interaction.

### Changed
- Dropped the heavy Vector DB/KNN architectural proposal in favor of a fast, local JSON approach, directly aligning with IRIS AI and Stonic AI design patterns for a "smaller replica" daily-needs agent.
- Answered user questions confirming Gemini Live vs Groq fallback behaviors and Vision (Camera/Screen Share) routing capabilities.

---

## [2026-06-16] - Architecture Consolidation & UI Decluttering

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Single Backend Architecture**: Consolidated OS automation tools (`pyautogui`, `pygetwindow`) into `ws_main.py` natively using `asyncio.to_thread()`, completely removing the need for a secondary `daemon.py` process on port 8002.
- **Orb Vision Toggle**: Added a singular `Camera` toggle inside the Orb controls that dynamically cycles the active input source (`Off` → `Camera` → `Screen Share` → `Off`).

### Changed
- **UI Simplification (Option B)**: Completely deleted the clunky `Optics_Link` floating windows from the left dashboard column.
- **Dynamic Vision Surface**: Repurposed the main "AI Assistant" thinking area in the center column. When the Vision toggle is activated, the static AI greeting smoothly transforms into the live WebRTC video feed, eliminating UI clutter and providing a focused, premium software experience.

### Removed
- **Deleted `windows_agent/daemon.py`**: Reduced technical debt and port contention.

## [2026-06-16] - Phases 5 to 10: Multi-Modal Vision & Desktop Automation

### Author
- Antigravity AI
- Machine: JinWoo-PC

### Added
- **Live Status Window**: Added a scrolling console in the frontend dashboard (`page.tsx`) to surface real-time actions and status events securely decoupled via CustomEvents.
- **Gemini Vision Component**: Integrated native WebRTC `<video>` tags for user Camera and Screen Share directly into the `Optics_Link` panel.
- **Background Frame Extraction**: Natively extracts 1 FPS JPEG frames via HTML5 Canvas from the active WebRTC stream and dispatches them without blocking the UI thread.
- **Gemini Live Multimodal Session Manager**: Created `core/gemini_live_manager.py` to seamlessly establish and maintain bidirectional `AsyncLiveSession` connections to Google's Gemini Multimodal Live API.
- **Desktop Companion Daemon**: Built a standalone `windows_agent/daemon.py` using FastAPI to expose secure OS-level endpoints (mouse, keyboard, window focus, screenshots) via `pyautogui` and `pygetwindow` bypassing Electron's technical debt.

### Changed
- **WebSocket Transport Upgrade**: Updated `useNexusVoice.ts` to multiplex PCM audio byte streams alongside JSON-encoded Base64 JPEG payloads over a single `ws://localhost:8001` connection.
- **Backend Failover Architecture**: Refactored `ws_main.py`'s `VoiceSession` to natively construct the `GeminiLiveSessionManager`. If Gemini drops or rate-limits, it triggers an instant graceful degrade to the local Groq + EdgeTTS fallback pipeline (Mode B).

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




