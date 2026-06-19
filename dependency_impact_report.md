# Dependency Impact Report: Renaming `voice_agent` to `nexus_core`

This report catalogs all occurrences of the `voice_agent` directory name in code, configuration, scripts, and documentation, and defines the replacement mapping.

## Impact Summary

- **Total References Found:** 12 files (excluding changelogs and archived docs)
- **Relative/Internal Imports:** None. All internal backend python imports use relative imports (`from core.x import y`) or direct local imports, meaning renaming the root directory will **not** break python module resolution.
- **Frontend References:** None. The Next.js frontend communicates with the backend exclusively over HTTP/WS endpoints (`http://localhost:8001/`), so no frontend files are impacted.
- **Script & Config References:** 6 files (including launcher scripts, environment managers, and Pyright configuration). These are the critical path targets.

---

## Catalog of References & Modification Plan

### 1. Launcher & Boot Scripts

#### [MODIFY] [StartBackend.ps1](file:///d:/AI/StartBackend.ps1#L7)
- **Current (Line 7):**
  ```powershell
  $BACKEND_ROOT = "$PROJECT_ROOT\backend\voice_agent"
  ```
- **Replacement:**
  ```powershell
  $BACKEND_ROOT = "$PROJECT_ROOT\backend\nexus_core"
  ```

#### [MODIFY] [run.ps1](file:///d:/AI/run.ps1#L35-L37)
- **Current (Lines 35, 37):**
  ```powershell
  $backend_cmd = "cd backend/voice_agent; ..\venv\Scripts\python.exe main.py serve"
  $chat_cmd = "cd backend/voice_agent; ..\venv\Scripts\python.exe chat.py"
  ```
- **Replacement:**
  ```powershell
  $backend_cmd = "cd backend/nexus_core; ..\venv\Scripts\python.exe main.py serve"
  $chat_cmd = "cd backend/nexus_core; ..\venv\Scripts\python.exe chat.py"
  ```

---

### 2. Workspace & IDE Configurations

#### [MODIFY] [pyrightconfig.json](file:///d:/AI/pyrightconfig.json#L6-L10)
- **Current (Lines 6, 10):**
  ```json
          "backend/voice_agent"
          "d:/AI/backend/voice_agent"
  ```
- **Replacement:**
  ```json
          "backend/nexus_core"
          "d:/AI/backend/nexus_core"
  ```

---

### 3. Backend Code Configurations

#### [MODIFY] `backend/voice_agent/config.py` (to become [config.py](file:///d:/AI/backend/nexus_core/config.py#L30))
- **Current (Line 30):**
  ```python
  BASE_PIPER          = "D:/AI/backend/voice_agent/models/piper"
  ```
- **Replacement:**
  ```python
  BASE_PIPER          = "D:/AI/backend/nexus_core/models/piper"
  ```

#### [MODIFY] `backend/voice_agent/core/gemini_live_manager.py` (to become [gemini_live_manager.py](file:///d:/AI/backend/nexus_core/core/gemini_live_manager.py#L16-L23))
- **Current (Lines 16, 23):**
  ```python
      fh = logging.FileHandler('d:/AI/backend/voice_agent/DEBUG_GEMINI_RAW.log', encoding='utf-8')
      fh = logging.FileHandler('d:/AI/backend/voice_agent/DEBUG_GEMINI_SESSION.log', encoding='utf-8')
  ```
- **Replacement:**
  ```python
      fh = logging.FileHandler('d:/AI/backend/nexus_core/DEBUG_GEMINI_RAW.log', encoding='utf-8')
      fh = logging.FileHandler('d:/AI/backend/nexus_core/DEBUG_GEMINI_SESSION.log', encoding='utf-8')
  ```

---

### 4. Tests & Benchmark Suites

#### [MODIFY] `backend/voice_agent/test_v1.py` (to become [test_v1.py](file:///d:/AI/backend/nexus_core/test_v1.py#L18))
- **Current (Line 18):**
  ```python
  sys.path.append(os.path.join(backend_dir, "voice_agent"))
  ```
- **Replacement:**
  ```python
  sys.path.append(os.path.join(backend_dir, "nexus_core"))
  ```

#### [MODIFY] [test_edge_tts.py](file:///d:/AI/backend/test_edge_tts.py#L6)
- **Current (Line 6):**
  ```python
          from voice_agent.providers.tts_edge import EdgeTTS
  ```
- **Replacement:**
  ```python
          from nexus_core.providers.tts_edge import EdgeTTS
  ```

#### [MODIFY] [event_loop_latency_piper.py](file:///d:/AI/tests/event_loop_latency_piper.py#L5), [event_loop_latency.py](file:///d:/AI/tests/event_loop_latency.py#L5), [chunk_size_benchmark.py](file:///d:/AI/tests/chunk_size_benchmark.py#L5)
- **Current (Line 5):**
  ```python
  sys.path.append('d:/AI/backend/voice_agent')
  ```
- **Replacement:**
  ```python
  sys.path.append('d:/AI/backend/nexus_core')
  ```

---

### 5. Scratch & Helper Tools

#### [MODIFY] [check_gemini.py](file:///d:/AI/scratch/check_gemini.py#L5-L6), [update_env.py](file:///d:/AI/scratch/update_env.py#L5)
- **Current:**
  ```python
  load_dotenv("d:/AI/backend/voice_agent/.env")
  env_path = r'd:\AI\backend\voice_agent\.env'
  ```
- **Replacement:**
  ```python
  load_dotenv("d:/AI/backend/nexus_core/.env")
  env_path = r'd:\AI\backend\nexus_core\.env'
  ```

---

## Verification & Execution Steps

1. Execute code modifications in all unstaged files above.
2. Rename the directory `backend/voice_agent/` to `backend/nexus_core/`.
3. Run `backend/venv/Scripts/python.exe backend/nexus_core/test_v1.py` to ensure all 22 tests pass seamlessly.
