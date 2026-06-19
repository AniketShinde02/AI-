"""
execution_hooks.py
==================
Phase 4 — Verification Layer Hooks

Mandatory pre/post execution hooks for every tool capability.
Wraps the execution contract with:
  - Pre-execution permission gate (already in voice_session.py, audited here)
  - Post-execution contract validation
  - Verification DB write (async, non-blocking)
  - Structured execution trace for UI

All tool categories covered:
  - Desktop (pc_*)
  - Browser (browser_*)
  - Files (read_file, write_file, read_directory)
  - Memory (update_preferences, get_user_memory)

Contract shape enforced:
  {
    "success": bool,
    "verified": bool,
    "execution_time": str,   # e.g. "0.41s"
    "tool": str,
    "target": str,
    "error": str | None,
    "result": str | None,    # human-readable result summary
  }
"""

import time
import logging
import asyncio
from typing import Any, Dict, Optional

from core.database import db

logger = logging.getLogger("nexus.execution_hooks")


async def broadcast_workspace_state(
    active_capability: Optional[str] = None,
    status: str = "idle",
    verification_state: Optional[str] = None,
    current_task: Optional[str] = None,
    tool_target: Optional[str] = None,
    execution_time: Optional[str] = None,
    last_result: Optional[str] = None,
    browser_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Broadcast current workspace state updates to all active client WebSocket sessions."""
    try:
        import core.global_state as gs
        if not gs.active_sessions:
            return

        # Query active window title
        active_window_title = "Desktop"
        if gs.gw:
            try:
                win = gs.gw.getActiveWindow()
                if win and win.title:
                    active_window_title = win.title
            except Exception:
                pass

        # Query browser screenshot (base64)
        from core.browser_agent import browser_agent
        browser_screenshot = await browser_agent.get_screenshot_base64()

        for session in list(gs.active_sessions.values()):
            if not session.is_connected:
                continue

            task = current_task or getattr(session, "current_task", None)

            # Phase D: Include browser memory state if available
            browser_memory = browser_state or browser_agent.get_workspace_state()

            payload = {
                "type": "workspace_state",
                "data": {
                    "current_task": task,
                    "active_capability": active_capability,
                    "tool_target": tool_target,
                    "execution_time": execution_time,
                    "last_result": last_result,
                    "status": status,
                    "verification_state": verification_state,
                    "active_window": active_window_title,
                    "browser_screenshot": browser_screenshot,
                    "browser_memory": browser_memory,
                }
            }
            await session.safe_send_json(payload)
    except Exception as e:
        logger.error(f"❌ Failed to broadcast workspace state: {e}", exc_info=True)



# ---------------------------------------------------------------------------
# Contract validator
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"success", "verified"}


def validate_contract(result: Dict[str, Any], tool_id: str) -> Dict[str, Any]:
    """
    Ensure the execution result conforms to the Nexus contract.
    Missing keys are added with safe defaults.
    Logs a warning if the contract was incomplete.
    """
    if not isinstance(result, dict):
        result = {"success": False, "verified": False, "error": str(result), "result": ""}

    missing = REQUIRED_KEYS - result.keys()
    if missing:
        logger.warning(f"⚠️ [Contract] Tool '{tool_id}' returned incomplete contract. Missing: {missing}")
        for key in missing:
            result[key] = False

    # Normalize optional fields
    result.setdefault("tool", tool_id)
    result.setdefault("target", "")
    result.setdefault("error", None)
    result.setdefault("result", "")
    result.setdefault("execution_time", "0.00s")

    return result


# ---------------------------------------------------------------------------
# Post-execution verification write (non-blocking)
# ---------------------------------------------------------------------------

def _log_verification_bg(tool_id: str, result: Dict[str, Any]) -> None:
    """Fire-and-forget verification DB write so execution path isn't blocked."""
    status = "PASS" if result.get("success") and result.get("verified") else "FAIL"
    evidence = result.get("result") or result.get("error") or ""
    contract_str = (
        f"success={result.get('success')} verified={result.get('verified')} "
        f"time={result.get('execution_time', '?')}"
    )
    asyncio.create_task(
        db.log_verification(tool_id, status, contract_str, str(evidence))
    )


# ---------------------------------------------------------------------------
# Core hook: wrap_execution
# ---------------------------------------------------------------------------

async def wrap_execution(
    tool_id: str,
    target: str,
    execute_coro,       # coroutine that runs the actual tool
    category: str = "system",
) -> Dict[str, Any]:
    """
    Wraps any tool execution with timing, contract validation, and verification logging.

    Usage in voice_session.py / routes:
        result = await wrap_execution(
            tool_id="pc_open_app",
            target="notepad",
            execute_coro=pc_controller.open_app("notepad"),
            category="desktop",
        )

    Returns a fully validated execution contract dict.
    """
    await broadcast_workspace_state(
        active_capability=tool_id,
        status="running",
        verification_state="pending",
        tool_target=target,
    )

    t_start = time.perf_counter()
    raw_result: Dict[str, Any] = {"success": False, "verified": False, "error": None, "result": ""}

    try:
        logger.info(f"🔧 [Hook] Executing '{tool_id}' → target='{target}' category={category}")
        raw_result = await execute_coro
        if raw_result is None:
            raw_result = {"success": False, "verified": False, "error": "Tool returned None"}
    except Exception as e:
        raw_result = {
            "success": False,
            "verified": False,
            "error": f"{type(e).__name__}: {e}",
            "result": "",
        }
        logger.error(f"❌ [Hook] Tool '{tool_id}' raised: {e}", exc_info=True)
    finally:
        elapsed = time.perf_counter() - t_start
        raw_result["execution_time"] = f"{elapsed:.2f}s"
        raw_result.setdefault("tool", tool_id)
        raw_result.setdefault("target", target)

    contract = validate_contract(raw_result, tool_id)

    # Non-blocking DB write
    _log_verification_bg(tool_id, contract)

    status_emoji = "✅" if contract.get("success") else "❌"
    logger.info(
        f"{status_emoji} [Hook] '{tool_id}' → success={contract['success']} "
        f"verified={contract['verified']} time={contract['execution_time']}"
    )

    v_state = "passed" if contract.get("success") and contract.get("verified") else "failed"
    status_state = "completed" if contract.get("success") else "failed"
    result_summary = str(contract.get("result") or contract.get("error") or "")[:200]
    await broadcast_workspace_state(
        active_capability=tool_id,
        status=status_state,
        verification_state=v_state,
        tool_target=target,
        execution_time=contract.get("execution_time"),
        last_result=result_summary,
    )

    return contract



# ---------------------------------------------------------------------------
# Category-specific convenience wrappers
# ---------------------------------------------------------------------------

async def run_desktop_tool(tool_id: str, target: str, execute_coro) -> Dict[str, Any]:
    """Hook for pc_* tools."""
    return await wrap_execution(tool_id, target, execute_coro, category="desktop")


async def run_browser_tool(tool_id: str, target: str, execute_coro) -> Dict[str, Any]:
    """Hook for browser_* tools."""
    return await wrap_execution(tool_id, target, execute_coro, category="browser")


async def run_file_tool(tool_id: str, target: str, execute_coro) -> Dict[str, Any]:
    """Hook for file_read / file_write tools."""
    return await wrap_execution(tool_id, target, execute_coro, category="files")


async def run_memory_tool(tool_id: str, target: str, execute_coro) -> Dict[str, Any]:
    """Hook for update_preferences / get_user_memory tools."""
    return await wrap_execution(tool_id, target, execute_coro, category="memory")
