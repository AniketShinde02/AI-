# Nexus Desktop Skills Library

This document defines the official Desktop automation skills supported by Nexus. 
These skills are invoked by the Action Router or Planner and map to capabilities in `core/capability_registry_def.py`.

## 1. Open Application (`pc_open_app`)
- **Required Capabilities**: `pc_open_app`
- **Preconditions**: OS is Windows, application is installed locally.
- **Verification**: Verifies active window title matches target app post-launch.
- **Recovery**: None. If missing, reports failure.
- **Example Prompt**: "Open Notepad", "Launch Chrome"

## 2. Close Application (`pc_close_app`)
- **Required Capabilities**: `pc_close_app`
- **Preconditions**: App is currently running.
- **Verification**: Polling process list to ensure termination.
- **Recovery**: Sends SIGKILL if SIGTERM fails.
- **Example Prompt**: "Close Word", "Kill Discord"

## 3. Window Management (`pc_minimize_app`, `pc_maximize_app`, `pc_focus_app`, `pc_switch_window`)
- **Required Capabilities**: `pc_minimize_app`, `pc_maximize_app`, `pc_focus_app`, `pc_switch_window`
- **Preconditions**: Target app exists in current session.
- **Verification**: Checks `DesktopContext.active_window`.
- **Recovery**: None.
- **Example Prompt**: "Minimize Chrome", "Switch to VS Code"

## 4. File Operations (`pc_file_explorer`)
- **Required Capabilities**: `pc_file_explorer`
- **Preconditions**: Valid target directory or file.
- **Verification**: Verifies `explorer.exe` spawned on target path.
- **Recovery**: Falls back to user directory if target path doesn't exist.
- **Example Prompt**: "Open my Downloads folder"

## 5. Clipboard Control (`pc_clipboard_read`, `pc_clipboard_write`)
- **Required Capabilities**: `pc_clipboard_read`, `pc_clipboard_write`
- **Preconditions**: Clipboard must not be locked by another process.
- **Verification**: Validates clipboard content length.
- **Recovery**: Falls back to PowerShell clipboard commands if `win32clipboard` throws access error.
- **Example Prompt**: "Read my clipboard", "Copy this text"

## 6. Mouse & Keyboard Control (`pc_click`, `pc_move_mouse`, `pc_drag`, `pc_scroll`, `pc_type_text`, `pc_press_shortcut`)
- **Required Capabilities**: `pc_type_text`, `pc_press_shortcut`, `pc_move_mouse`, `pc_click`, `pc_drag`, `pc_scroll`
- **Preconditions**: Target UI must be in focus.
- **Verification**: Assumed visual verification by default.
- **Recovery**: None.
- **Example Prompt**: "Click at 500, 200", "Type hello world", "Press Ctrl+C"

## 7. Screenshots (`pc_take_screenshot`)
- **Required Capabilities**: `pc_take_screenshot`
- **Preconditions**: None.
- **Verification**: Base64 output length check.
- **Recovery**: Falls back to PowerShell screenshot module if `PIL` fails.
- **Example Prompt**: "Take a screenshot of my desktop"
