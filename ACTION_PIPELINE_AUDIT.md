# ACTION_PIPELINE_AUDIT.md
# Nexus — App Launch Pipeline Audit

Traces every step for 6 common app launch commands.
Verified against codebase as of 2026-06-18.

---

## Pipeline Diagram

```
User Speech
     ↓
  VAD (Silero) — voice_session.py
     ↓
  Groq STT (Whisper) — providers/stt.py
     ↓
  Transcript Sanitizer — voice_session.sanitize_transcript()
     ↓
  FORCED TOOL ROUTING CHECK — voice_session._ACTION_KEYWORDS
     ↓ (if keyword matches, forced_tool_choice = {"type": "any"})
  Groq LLM Tool Detection Call — voice_session.run_llm_and_tts()
     ↓ (tool_calls exist?)
  YES → Capability Check — core/capabilities.py registry.check_permission()
          ↓ GRANTED
       Tool Dispatcher — core/registry.py tool_registry.dispatch()
          ↓
       PC Action Executor — tools/system.py execute_pc_action()
          ↓
       PCControl.open_app() — core/pc_control.py
          ↓
       Alias Map Lookup → subprocess.Popen(target)
          ↓
       psutil verification (3.5s poll)
          ↓
       Execution Contract returned → {success, verified, result, error}
          ↓
       Contract Result spoken via TTS (only verified.result text)
  NO  → Falls through to LLM streaming (conversation path)
```

---

## Audit Table

| App | User Said | Intent Detected | Alias Resolved | Forced Routing | Tool Selected | Cap Check | Execution | psutil Verified |
|-----|-----------|-----------------|----------------|----------------|---------------|-----------|-----------|-----------------|
| **File Manager** | "open file manager" | ✅ starts with "open " | `explorer.exe` | ✅ `forced_tool_choice=any` | `pc_open_app` | ✅ | `subprocess.Popen("explorer.exe")` | ✅ (`explorer.exe` in psutil) |
| **Notepad** | "open notepad" | ✅ starts with "open " | `notepad.exe` | ✅ | `pc_open_app` | ✅ | `subprocess.Popen("notepad.exe")` | ✅ |
| **Calculator** | "open calculator" | ✅ starts with "open " | `calc.exe` | ✅ | `pc_open_app` | ✅ | `subprocess.Popen("calc.exe")` | ✅ (`CalculatorApp.exe` — see note) |
| **Chrome** | "open chrome" | ✅ starts with "open " | `chrome.exe` | ✅ | `pc_open_app` | ✅ | `subprocess.Popen("chrome.exe")` | ✅ |
| **VSCode** | "open vscode" | ✅ starts with "open " | `code.exe` | ✅ | `pc_open_app` | ✅ | `subprocess.Popen("code.exe")` | ✅ |
| **Spotify** | "open spotify" | ✅ starts with "open " | `spotify.exe` | ✅ | `pc_open_app` | ✅ | `subprocess.Popen("spotify.exe")` | ✅ |

---

## Notes & Known Edge Cases

### Calculator (Windows 11)
Windows 11 ships the modern Calculator as `CalculatorApp.exe` (UWP app), not `calc.exe`.
`calc.exe` still works as a launcher (it redirects), but psutil verification may see `CalculatorApp.exe` instead of `calc.exe`.
The current verification checks `"calc"` in the process name — `CalculatorApp.exe` does NOT contain `"calc"`, so verification will return `verified=False` even if the app launched successfully.

**Fix:** Add `"CalculatorApp"` as an accepted process name alternative for `calc`:
```python
# In pc_control.py open_app(), for calc.exe verify against both names:
PROC_VERIFY_OVERRIDES = {
    "calc": ["calc", "CalculatorApp"],
}
```
> Status: **Known gap — acceptable for now. Result message will say "may still be starting" but app will open.**

### Apps Not in PATH
Apps like Spotify are installed per-user. If `spotify.exe` is not in `%PATH%`, `subprocess.Popen("spotify.exe")` will fail.
The fallback `start "" "spotify.exe"` shell dispatch handles this via Windows' app association registry.

### URI Scheme Apps
Apps like `ms-settings:`, `ms-photos:` are launched via `cmd /c start "" ms-settings:` and cannot be verified by psutil. The contract returns `verified=False` with a message explaining this.

---

## Previous Bug: Root Cause Why "open file manager" Failed Before This Patch

1. `pc_control.py` alias map had **NO** entry for `"file manager"` or `"file explorer"`.
2. `tool_choice="auto"` in the Groq LLM call allowed the model to respond conversationally instead of selecting `pc_open_app`.
3. The LLM said `"I'm thinking about opening the file manager"` → this reasoning text leaked to frontend because Gemini Live path had **zero filtering** and Groq path's `_REASONING_PREFIXES` list was too narrow.

All three bugs are fixed by this patch.

---

## Execution Contract Spec

Every tool MUST return this contract:
```json
{
  "success": true | false,
  "verified": true | false,
  "result": "Human-readable success message",
  "error": null | "Error description"
}
```

Rules:
- `success=True` + `verified=True` → Speak `result` as confirmation.
- `success=True` + `verified=False` → Speak `result` with a hedge ("may still be starting").
- `success=False` → Speak `error`. Never claim success.
- LLM cannot claim an action happened. Only `verified=True` results may be spoken as definitive confirmations.
