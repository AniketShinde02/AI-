# Changelog

## [2026-06-29] — Nexus V1.6 Code Quality & Type Safety Audit

### Author
- Antigravity AI
- Machine: Local-Windows-PC

### Fixed
- **`core/planner/executor.py`**: Removed two orphaned imports (`from core.task_cards import task_card_engine` and duplicate `from core.workspace import workspace_manager`) that were accidentally placed outside any function or class at line 31-32. This resolves Pyrefly emitting cascading false-positive parse errors across the file.
- **`tests/test_workspace_integration.py`**: Fixed a stale `execution_hooks` import that was broken after the V1.6 refactor. Pointed the import to the correct module: `core.workspace.broadcast`.
- **`core/executors/desktop_executor.py`**: Fixed a type mismatch bug on `pc_controller.click()`'s double parameter. The executor was passing an `int` for `double`, which was strictly typed as `bool`. Now explicitly cast using `bool()`.
- **`tests/run_validation.py`**: Fixed a signature mismatch for `model_router.route_task`. The function was being called with raw string positional arguments. Refactored the call to properly pass named arguments (`task_class=TaskClass.FAST_ROUTING`, `system_prompt`, `messages`).
- **`archive_experiments/main.py`**: Fixed syntax/typing errors to preserve archive validity:
  - Guarded `GROQ_API_KEY` with `or ""` to satisfy the `str` type contract (preventing `str | None` mismatch).
  - Removed the invalid `stt.silence_threshold` attribute assignment (no longer exists on `GroqSTT`).
  - Added missing async stubs for legacy procedural tools (`run_command`, `open_application`, `create_note`, `create_task`) to prevent import and undefined variable crashes.

### Changed
- **`core/executors/base.py` & `browser_executor.py` & `memory_executor.py`**: Added explicit `None` fallback guards (`or ""`) to dictionary `.get()` extractions for `target`, `goal`, and `session_id`. This ensures the strict `str` type contracts are met, eliminating Pyrefly static type warnings and preventing potential runtime `TypeError` crashes.
- **`config.py`**: Added explicit `bool` type hint to `ENABLE_DAG_ORCHESTRATOR` (`ENABLE_DAG_ORCHESTRATOR: bool = False`) to prevent Pyrefly from inferring `Literal[False]`, which was blocking test environments from dynamically toggling the flag to `True`.
- **`tests/benchmark_suite.py`**: Added explicit `Dict[str, Any]` typing to the `result` dictionaries inside the benchmark loop to satisfy Pyrefly static analysis and resolve type assignment errors.

### Notes
- **Context on `current_problems` errors:** The majority of the reported parse errors (e.g., `unexpected indentation`, `cannot find name 'graph'`) were **false positives** originating from Pyrefly's virtual in-memory snippet analyzer (`d:\\__pyrefly_virtual__\\inmemory\\*.py`). The root cause was the orphaned import lines in `executor.py` disrupting Pyrefly's code block boundaries.
- **Context on missing modules:** Errors reporting `Cannot find module 'fastapi'`, `pydantic`, `PIL`, etc., are **false positives** caused by the IDE language server strictly querying `.venv` instead of the globally managed `uv` environment or custom virtual environment where the packages actually reside.
- No new logical features were added; this was a strict zero-tolerance code quality and type safety sweep.

---



## [2026-06-29] — voice_session.py Legacy Dispatch Refactor

### Author
- Antigravity AI
- Machine: Local-Windows-PC

### Fixed
- `ModuleNotFoundError: No module named 'tools.task_tools'` — removed dead `create_task`/`create_note` import from `voice_session.py` (functions were imported but never called in the module body).
- Replaced the entire legacy tool dispatch block in `voice_session.py` (lines ~195-263) that still used `run_desktop_tool`, `execute_pc_action`, `run_browser_tool`, `execute_browser_action`, `run_automation_tool` — all from deleted modules — with a unified `get_executor()` dispatch matching the V1.6 Domain Executor pattern.
- Fixed `test_phase_cd.py` to use `DesktopExecutor` / `BrowserExecutor` instead of deleted `tools.system` and `tools.browser_tools`.
- Removed remaining dead `task_tools` import from `archive_experiments/main.py`.

### Verified
- Ripgrep scans confirm zero remaining references to: `tools.task_tools`, `tools.browser_tools`, `tools.system`, `run_desktop_tool`, `run_browser_tool`, `core.execution_hooks`.

---


## [2026-06-29] — Nexus V1.6 Import Cleanup & Benchmark Verification

### Author
- Antigravity AI
- Machine: Local-Windows-PC

### Fixed
- Fixed second stale `from core.execution_hooks import broadcast_workspace_state` in `model_router.py` line 334 (inside 429 fallback handler) — root cause of all benchmark FAIL cases.
- Fixed `UnicodeEncodeError` in `tests/benchmark_suite.py` on Windows cp1252 terminals — replaced emoji header with ASCII and switched to `sys.stdout.buffer.write(report.encode('utf-8'))`.
- Removed dead unused imports (`read_file`, `write_file`, `get_weather`) from `core/global_state.py`.

### Verified
- Ripgrep scan confirms **zero remaining** `from core.execution_hooks import` references across entire `nexus_core` codebase.
- Benchmark suite `tests/benchmark_suite.py` completed: **10/10 PASS (100%)**, Avg Latency 18340ms.
- Dashboard written to `tests/benchmark_dashboard.md`.

---

## [2026-06-29] — Nexus V1.6 Domain Executor Framework Refactor

### Author
- Antigravity AI
- Machine: Local-Windows-PC

### Added
- Created `core/executors/base.py` introducing the `BaseExecutor` abstract contract.
- Built 7 isolated domain executors: `DesktopExecutor`, `BrowserExecutor`, `VisionExecutor`, `MemoryExecutor`, `ResearchExecutor`, `VerificationExecutor`, `RecoveryExecutor`.
- Created `core/workspace/broadcast.py` as a standalone helper for broadcasting WebSocket state to clients, removing dependency coupling.

### Changed
- Refactored `core/planner/executor.py` to route all tasks through the dynamic `EXECUTOR_REGISTRY` instead of hardcoded procedural if-statements.
- Updated `core/voice_session.py`, `core/model_router.py`, `core/provider_governor.py`, `tests/stress_test_engine.py`, and `api/routes_system.py` to interface exclusively with the Domain Executors or the new generic broadcast helper.
- Overhauled `NEXUS_V1.md` Section 2.4 to document the object-oriented Domain Executor transition.

### Fixed
- Fixed cyclical import constraints and broken tool references across the `tools/__init__.py` registry.
- Fixed `test/benchmark_suite.py` regressions related to deleted execution hooks.

### Removed
- Deleted `core/execution_hooks.py` (legacy procedural hooks).
- Deleted procedural wrappers: `tools/browser_tools.py`, `tools/system.py`, `tools/scrapper_tools.py`, `tools/task_tools.py`.

### Architecture / Notes
- The Execution Engine is now strictly object-oriented.
- Providers (LLMs) supply reasoning, while Executors strictly perform deterministic work.
- The `WorkspaceManager`, `Planner`, and `Verification Engine` core paradigms remain untouched.
