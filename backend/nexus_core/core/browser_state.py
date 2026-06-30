"""
browser_state.py
================
Nexus BrowserAgent V1.2 — Browser State Machine

Enforces deterministic state transitions for the BrowserAgent.
Emits WebSocket broadcasts via WorkspaceManager whenever state changes.
"""
import enum
import logging
import asyncio
from typing import Optional, Dict, Any

from core.workspace.broadcast import broadcast_workspace_state
from core.workspace.workspace_manager import workspace_manager

logger = logging.getLogger("nexus.browser_state")


class BrowserStateEnum(str, enum.Enum):
    INITIALIZING = "initializing"
    LAUNCHING = "launching"
    READY = "ready"
    NAVIGATING = "navigating"
    WAITING = "waiting"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CLOSED = "closed"


class BrowserStateMachine:
    """
    Manages browser state transitions and broadcasts updates.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state = BrowserStateEnum.INITIALIZING
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> BrowserStateEnum:
        return self._state

    async def transition_to(self, new_state: BrowserStateEnum, metadata: Optional[Dict[str, Any]] = None):
        """
        Transition to a new state and broadcast to UI.
        """
        async with self._lock:
            old_state = self._state
            self._state = new_state
            
            logger.debug(f"[BrowserState:{self.session_id}] {old_state.value} → {new_state.value}")

            # Update WorkspaceManager's memory context if it exists
            try:
                # Get current browser state from WorkspaceManager
                ws = workspace_manager.get()
                if hasattr(ws, 'browser_memory') and ws.browser_memory:
                    ws.browser_memory['session_state'] = new_state.value
                    if metadata and 'url' in metadata:
                        ws.browser_memory['current_url'] = metadata['url']
                    if metadata and 'title' in metadata:
                        ws.browser_memory['page_title'] = metadata['title']
            except Exception as e:
                logger.warning(f"[BrowserState] Failed to update WorkspaceManager: {e}")

            # Broadcast the update
            try:
                await broadcast_workspace_state(
                    status=f"browser_{new_state.value}",
                    current_task=f"Browser {new_state.value}"
                )
            except Exception as e:
                logger.warning(f"[BrowserState] Broadcast failed: {e}")

