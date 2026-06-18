# Tool Execution Audit Report

## 1. Problem Statement
Nexus is currently exhibiting a hallucination failure: when instructed to perform an action (e.g., "open file manager"), the LLM immediately claims the action succeeded before verification or even execution completes. The reality often contradicts this claim.

## 2. Root Cause Analysis
- **Missing Contract**: Tools currently return raw strings or basic dictionaries without a strict schema.
- **Premature Confirmation**: In `voice_session.py`, `execute_pc_action` is called, but a hardcoded confirmation string (e.g., `f"Opening {app_name}."`) is passed to the TTS queue *regardless* of the actual outcome.
- **Lack of Verification**: Tools like `pc_open_app` use fire-and-forget methods (e.g., `subprocess.Popen`) and return `{"success": True}` without polling the OS to verify if the process actually started.

## 3. Tool Path Audit

### 3.1 PC Control (`tools/system.py` -> `core/pc_control.py`)
| Action | Intent Detected | Tool Selected | Tool Executed | Verification Performed | Success Returned |
|---|---|---|---|---|---|
| `pc_open_app` | Yes (`SYSTEM_TOOLS`) | Yes | Yes (`subprocess.Popen`) | **NO** (Fire-and-forget) | No (Returns string/dict) |
| `pc_close_app` | Yes | Yes | Yes (`psutil.kill`) | Partial (`killed > 0`) | No (Returns string) |
| `pc_type_text` | Yes | Yes | Yes (`pyautogui.write`) | **NO** | No |
| `pc_press_shortcut`| Yes | Yes | Yes (`pyautogui.hotkey`) | **NO** | No |
| `pc_take_screenshot`| Yes | Yes | Yes (`ImageGrab.grab()`) | Yes (File saved) | No |

### 3.2 File Tools (`tools/file_tools.py`)
| Action | Intent Detected | Tool Selected | Tool Executed | Verification Performed | Success Returned |
|---|---|---|---|---|---|
| `read_file` | Yes | Yes | Yes | Yes (Try/Catch) | No (Returns string) |
| `write_file` | Yes | Yes | Yes | Yes (Try/Catch) | No (Returns string) |
| `read_directory` | Yes | Yes | Yes | Yes | No (Returns string) |
| `search_files` | Yes | Yes | Yes | Yes | No (Returns string) |

### 3.3 Memory & Tasks (`tools/task_tools.py`, `tools/memory_tools.py`)
| Action | Intent Detected | Tool Selected | Tool Executed | Verification Performed | Success Returned |
|---|---|---|---|---|---|
| `create_task` | Yes | Yes | Yes | Yes (DB write) | No (Returns string) |
| `create_note` | Yes | Yes | Yes | Yes (DB write) | No (Returns string) |
| `get_memory` | Yes | Yes | Yes | Yes | No (Returns string) |

### 3.4 Third Party Tools (`tools/third_party_tools.py`)
| Action | Intent Detected | Tool Selected | Tool Executed | Verification Performed | Success Returned |
|---|---|---|---|---|---|
| `get_weather` | Yes | Yes | Yes | Yes (HTTP Check) | No (Returns string) |
| `search_web` | Yes | Yes | Yes | Yes (HTTP Check) | No (Returns string) |
| `read_webpage` | Yes | Yes | Yes | Yes (HTTP Check) | No (Returns string) |

## 4. The `Execution Contract` Standard
All tool endpoints will be refactored to return the following strict JSON schema:
```json
{
  "success": boolean,
  "verified": boolean,
  "result": string,
  "error": string | null
}
```

## 5. Required Architectural Changes
1. **Tool Refactoring**: Update all files in `tools/` and `core/` (like `pc_control.py`) to return the Execution Contract.
2. **Deep OS Verification**: Implement `psutil` or Window handle polling to strictly verify if an app opened before setting `verified: true`.
3. **Voice Session Refactoring**: In `voice_session.py`, remove hardcoded confirmations. Replace with a check: only pass the `result` string to TTS if `success` and `verified` are both `true`. Otherwise, pass the `error` string to TTS.
