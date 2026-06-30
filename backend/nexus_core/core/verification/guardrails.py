import re
import os
import logging
import asyncio
from typing import Dict, Tuple

logger = logging.getLogger("nexus.guardrails")

# Safe executables whitelist
SAFE_EXECUTABLES = {
    "notepad.exe",
    "mspaint.exe",
    "chrome.exe",
    "calc.exe",
    "explorer.exe",
    "edge.exe"
}

# Strict Blocked regex patterns (destructive actions)
BLOCKED_PATTERNS = [
    r"\b(rmdir|rm)\b\s+.*(-rf|/s|/q)",  # rm -rf or rmdir /s /q
    r"\bdel\b\s+.*(/s|/q)\s+c:\\windows",  # del C:\Windows
    r"\bformat\b\s+[c-z]:",  # disk formatting
    r"\breg\b\s+(delete|add)\b",  # destructive registry mods
    r"\bshutdown\b\s+.*(/s|/f|/t)",  # force shutdown
]

# Restricted command patterns requiring HITL Admin approval
RESTRICTED_PATTERNS = [
    r"\b(powershell|pwsh|cmd)\b",  # CLI shell execution
    r"\.exe\b",  # Direct executable launch
    r"\.(bat|ps1|msi|vbs|reg)\b",  # Scripting files execution
    r"\b(wget|curl|Invoke-WebRequest)\b",  # Remote downloads
]


class GuardrailPolicyEngine:
    """
    Scans and classifies local shell commands or executables.
    Manages async suspension events for Human-in-the-Loop (HITL) authorization.
    """
    def __init__(self):
        self._pending_approvals: Dict[str, asyncio.Event] = {}
        self._approval_status: Dict[str, bool] = {}

    def scan_command(self, command: str) -> Tuple[str, str]:
        """
        Classifies a command or executable target:
        Returns: (classification: 'PERMITTED' | 'RESTRICTED' | 'BLOCKED', reason: str)
        """
        cmd_lower = command.lower().strip()

        # Check blocklist first
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, cmd_lower):
                return "BLOCKED", f"Destructive command pattern matched blocklist rule: '{pattern}'"

        # Check safe executables whitelist first token
        tokens = cmd_lower.split()
        if tokens:
            exec_name = tokens[0].strip("\"'")
            exec_name = os.path.basename(exec_name)
            if exec_name in SAFE_EXECUTABLES:
                return "PERMITTED", "Safe execution path (whitelisted)"

        # Check restriction list
        for pattern in RESTRICTED_PATTERNS:
            if re.search(pattern, cmd_lower):
                return "RESTRICTED", f"Restricted operation matched rule: '{pattern}'"

        return "PERMITTED", "Safe execution path"

    async def request_authorization(self, session_id: str, command: str) -> bool:
        """
        Suspends execution, dispatches a WS authorization request, and waits for user input.
        """
        import core.global_state as gs

        # Register event
        event = asyncio.Event()
        self._pending_approvals[session_id] = event
        self._approval_status[session_id] = False

        # Find active session
        session = gs.active_sessions.get(session_id)
        if not session or not session.is_connected:
            logger.warning(f"⚠️ No active WebSocket session for {session_id} to prompt authorization. Denied.")
            return False

        logger.info(f"🛡️ [HITL] Suspended command for session {session_id}. Awaiting Admin authorization for: '{command}'")
        
        # Broadcast authorization modal event
        await session.safe_send_json({
            "type": "hitl_admin_permission",
            "data": {
                "session_id": session_id,
                "command": command,
            }
        })

        # Wait for the client to answer (timeout after 60 seconds)
        try:
            await asyncio.wait_for(event.wait(), timeout=60.0)
            approved = self._approval_status.get(session_id, False)
        except asyncio.TimeoutError:
            approved = False
            logger.warning(f"⏰ [HITL] Authorization request for session {session_id} timed out. Default to Denied.")
        finally:
            self._pending_approvals.pop(session_id, None)
            self._approval_status.pop(session_id, None)

        return approved

    def authorize_action(self, session_id: str, approved: bool) -> None:
        """Called when frontend returns authorization status via WebSocket."""
        if session_id in self._pending_approvals:
            self._approval_status[session_id] = approved
            self._pending_approvals[session_id].set()
            logger.info(f"🛡️ [HITL] Action resolved for session {session_id}. Approved={approved}")


# Singleton instance
guardrails = GuardrailPolicyEngine()
