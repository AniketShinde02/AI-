"""
workspace_manager.py
====================
The WorkspaceManager singleton — the single source of truth for all
Nexus runtime context.

Architecture:
  WorkspaceManager
    ├── DesktopContext   (TTL-cached OS/window queries)
    ├── BrowserContext   (wraps BrowserMemory + TTL screenshot)
    ├── ExecutionContext (mutable — updated by executor / hooks)
    ├── MemoryContext    (TTL-cached DB session turn count)
    └── ProviderContext  (TTL-cached governor sliding window)

Design rules:
  - NEVER call LLMs, tools, or perform planning
  - All collection is parallel (asyncio.gather)
  - Failures per sub-context are isolated — one failure does not break others
  - Singleton: import `workspace_manager` from core.workspace
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from core.workspace.workspace_state import WorkspaceState, SystemState
from core.workspace.desktop_context import DesktopContext
from core.workspace.browser_context import BrowserContext
from core.workspace.execution_context import ExecutionContext
from core.workspace.memory_context import MemoryContext
from core.workspace.provider_context import ProviderContext

logger = logging.getLogger("nexus.workspace.manager")

_TTL_SYSTEM = 5.0


class WorkspaceManager:
    """
    Orchestrates state collection from all sub-contexts.
    Exposes:
      - get(session_id)         → WorkspaceState
      - update_execution(**kw)  → update execution context
      - invalidate_screenshot() → force browser screenshot refresh
    """

    def __init__(self) -> None:
        self._desktop = DesktopContext()
        self._browser = BrowserContext()
        self._execution = ExecutionContext()
        self._memory = MemoryContext()
        self._provider = ProviderContext()

        # System metrics cache
        self._system_cache: Optional[SystemState] = None
        self._system_ts: float = 0.0

    # ------------------------------------------------------------------
    # Primary public API
    # ------------------------------------------------------------------

    async def get(self, session_id: str = "default") -> WorkspaceState:
        """
        Collect and return full WorkspaceState.
        All sub-contexts collected in parallel.
        """
        results = await asyncio.gather(
            self._desktop.collect(),
            self._browser.collect(session_id),
            self._memory.collect(session_id),
            self._provider.collect(),
            self._collect_system(),
            return_exceptions=True,
        )

        desktop    = results[0] if not isinstance(results[0], Exception) else None
        browser    = results[1] if not isinstance(results[1], Exception) else None
        memory     = results[2] if not isinstance(results[2], Exception) else None
        provider   = results[3] if not isinstance(results[3], Exception) else None
        system     = results[4] if not isinstance(results[4], Exception) else None

        # Log any failures (non-fatal)
        for i, label in enumerate(["desktop", "browser", "memory", "provider", "system"]):
            if isinstance(results[i], Exception):
                logger.warning(f"⚠️ WorkspaceManager: {label} context failed: {results[i]}")

        from core.workspace.workspace_state import (
            DesktopState, BrowserState, MemoryState, ProviderState
        )

        return WorkspaceState(
            desktop=desktop or DesktopState(),
            browser=browser or BrowserState(),
            execution=self._execution.snapshot(),
            memory=memory or MemoryState(session_id=session_id),
            provider=provider or ProviderState(),
            system=system or SystemState(),
        )

    # ------------------------------------------------------------------
    # Mutation API — called by executor.py and execution_hooks.py
    # ------------------------------------------------------------------

    def update_execution(
        self,
        status: Optional[str] = None,
        active_capability: Optional[str] = None,
        verification_state: Optional[str] = None,
        last_result: Optional[str] = None,
        execution_time: Optional[str] = None,
        current_task: Optional[str] = None,
    ) -> None:
        if current_task is not None:
            self._execution.set_task(current_task)
        if status is not None:
            self._execution.set_status(
                status=status,
                active_capability=active_capability,
                verification_state=verification_state,
                last_result=last_result,
                execution_time=execution_time,
            )

    def update_dag_node(
        self,
        graph_id: Optional[str] = None,
        node_id: Optional[str] = None,
        retries: int = 0,
    ) -> None:
        self._execution.set_dag_node(graph_id, node_id, retries)

    def reset_execution(self) -> None:
        self._execution.reset()

    def invalidate_screenshot(self) -> None:
        self._browser.invalidate_screenshot()

    # ------------------------------------------------------------------
    # Clipboard — explicit-only (not polled)
    # ------------------------------------------------------------------

    async def get_clipboard(self) -> Optional[str]:
        return await self._desktop.get_clipboard()

    # ------------------------------------------------------------------
    # System metrics (CPU/RAM)
    # ------------------------------------------------------------------

    async def _collect_system(self) -> SystemState:
        now = time.monotonic()
        if self._system_cache and (now - self._system_ts) < _TTL_SYSTEM:
            return self._system_cache
        state = await asyncio.to_thread(self._collect_system_sync)
        self._system_cache = state
        self._system_ts = now
        return state

    def _collect_system_sync(self) -> SystemState:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            return SystemState(cpu_percent=cpu, ram_percent=ram)
        except Exception as e:
            logger.debug(f"System metrics failed: {e}")
            return SystemState()


# ---------------------------------------------------------------------------
# Module-level singleton — import this, not the class
# ---------------------------------------------------------------------------
workspace_manager = WorkspaceManager()
