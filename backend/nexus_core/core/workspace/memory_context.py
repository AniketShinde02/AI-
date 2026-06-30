"""
memory_context.py
=================
Collects session/conversation memory state.

Design rules:
  - No LLM calls — only DB reads (session history count)
  - Cached for 5s — history count doesn't change per-request
  - Falls back gracefully if DB or lance_memory unavailable
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from core.workspace.workspace_state import MemoryState

logger = logging.getLogger("nexus.workspace.memory")

_TTL_MEMORY = 5.0


class MemoryContext:
    """
    Gathers session / memory state.  Consumed only by WorkspaceManager.
    """

    def __init__(self) -> None:
        self._cache: Optional[MemoryState] = None
        self._cache_ts: float = 0.0
        self._session_id: str = ""

    async def collect(self, session_id: str) -> MemoryState:
        now = time.monotonic()
        # Cache invalidation on session switch or TTL expiry
        if (
            self._cache
            and self._session_id == session_id
            and (now - self._cache_ts) < _TTL_MEMORY
        ):
            return self._cache

        recent_turns = await self._count_turns(session_id)
        state = MemoryState(
            session_id=session_id,
            recent_turns=recent_turns,
            active_project=None,  # Future: pull from workspace settings DB
        )
        self._cache = state
        self._cache_ts = now
        self._session_id = session_id
        return state

    async def _count_turns(self, session_id: str) -> int:
        try:
            from core.database import db
            history = await db.get_session_history(session_id, limit=50)
            return len(history)
        except Exception as e:
            logger.debug(f"Memory context DB read failed: {e}")
            return 0
