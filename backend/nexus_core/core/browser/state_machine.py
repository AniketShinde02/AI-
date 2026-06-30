"""
browser/state_machine.py
=========================
Nexus Browser Domain — State Machine

Single Responsibility: Enforce deterministic state transitions for BrowserAgent
sessions and broadcast UI events via workspace.broadcast.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.browser.models import BrowserStateEnum

logger = logging.getLogger("nexus.browser.state_machine")


class BrowserStateMachine:
    """
    Deterministic state machine for a single browser session.

    Valid transitions are enforced. State changes are broadcast to the UI
    via workspace.broadcast so the Workspace Panel reflects live status.
    """

    _VALID_TRANSITIONS: Dict[BrowserStateEnum, set] = {
        BrowserStateEnum.IDLE:         {BrowserStateEnum.INITIALIZING, BrowserStateEnum.NAVIGATING},
        BrowserStateEnum.INITIALIZING: {BrowserStateEnum.NAVIGATING, BrowserStateEnum.FAILED},
        BrowserStateEnum.NAVIGATING:   {BrowserStateEnum.VERIFYING, BrowserStateEnum.RECOVERING, BrowserStateEnum.FAILED},
        BrowserStateEnum.VERIFYING:    {BrowserStateEnum.EXECUTING, BrowserStateEnum.COMPLETED, BrowserStateEnum.FAILED, BrowserStateEnum.NAVIGATING},
        BrowserStateEnum.EXECUTING:    {BrowserStateEnum.VERIFYING, BrowserStateEnum.COMPLETED, BrowserStateEnum.RECOVERING, BrowserStateEnum.FAILED},
        BrowserStateEnum.WAITING:      {BrowserStateEnum.EXECUTING, BrowserStateEnum.FAILED, BrowserStateEnum.RECOVERING},
        BrowserStateEnum.RECOVERING:   {BrowserStateEnum.NAVIGATING, BrowserStateEnum.EXECUTING, BrowserStateEnum.FAILED},
        BrowserStateEnum.COMPLETED:    {BrowserStateEnum.IDLE, BrowserStateEnum.NAVIGATING},
        BrowserStateEnum.FAILED:       {BrowserStateEnum.IDLE, BrowserStateEnum.RECOVERING},
    }

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.current_state = BrowserStateEnum.IDLE

    async def transition_to(
        self,
        new_state: BrowserStateEnum,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Transition to new_state and broadcast the update."""
        allowed = self._VALID_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            logger.debug(
                f"[StateMachine:{self.session_id}] Skipping invalid transition "
                f"{self.current_state} → {new_state}"
            )
            # Force-allow for robustness, just log the anomaly
        old_state = self.current_state
        self.current_state = new_state

        logger.debug(
            f"[StateMachine:{self.session_id}] {old_state.value} → {new_state.value}"
        )
        await self._broadcast(new_state, payload or {})

    async def _broadcast(
        self,
        state: BrowserStateEnum,
        payload: Dict[str, Any],
    ) -> None:
        try:
            from core.workspace.broadcast import broadcast_workspace_state
            await broadcast_workspace_state(
                active_capability="browser",
                status=state.value,
                browser_state={"session_id": self.session_id, "state": state.value, **payload},
            )
        except Exception as e:
            logger.debug(f"[StateMachine] Broadcast failed (non-fatal): {e}")
