"""
execution_context.py
====================
Mutable execution state for the current running task / DAG.

Design rules:
  - Thread-safe updates via asyncio.Lock (no threading.Lock — all async)
  - executor.py and execution_hooks.py call update_*() methods
  - WorkspaceManager reads via snapshot()
  - NEVER calls LLMs, tools, or DB from here
"""
from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional

from core.workspace.workspace_state import ExecutionState

logger = logging.getLogger("nexus.workspace.execution")


class ExecutionContext:
    """
    Owns the single mutable ExecutionState for the active session.
    Updated by executor.py and execution_hooks.py.
    Read by WorkspaceManager.collect().
    """

    def __init__(self) -> None:
        self._state = ExecutionState()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Write API — called by executor.py / execution_hooks.py
    # ------------------------------------------------------------------

    def set_task(self, task: Optional[str]) -> None:
        self._state.current_task = task
        self._state.updated_at = time.time()

    def set_status(
        self,
        status: str,
        active_capability: Optional[str] = None,
        verification_state: Optional[str] = None,
        last_result: Optional[str] = None,
        execution_time: Optional[str] = None,
    ) -> None:
        self._state.status = status
        if active_capability is not None:
            self._state.active_capability = active_capability
        if verification_state is not None:
            self._state.verification_state = verification_state
        if last_result is not None:
            self._state.last_result = last_result
        if execution_time is not None:
            self._state.execution_time = execution_time
        self._state.updated_at = time.time()

    def set_dag_node(
        self,
        graph_id: Optional[str],
        node_id: Optional[str],
        retries: int = 0,
    ) -> None:
        self._state.dag_graph_id = graph_id
        self._state.dag_active_node = node_id
        self._state.dag_retries = retries
        self._state.updated_at = time.time()

    def reset(self) -> None:
        """Reset to idle after task completes."""
        self._state = ExecutionState()

    # ------------------------------------------------------------------
    # Read API — called by WorkspaceManager
    # ------------------------------------------------------------------

    def snapshot(self) -> ExecutionState:
        """Returns a copy of current execution state."""
        return self._state.model_copy()
