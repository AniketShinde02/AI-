"""
browser/session/pool.py
========================
Nexus Browser Domain — Session Pool

Single Responsibility: Manage the in-memory pool of SessionContext objects.
Provides get-or-create, close, and close-all operations.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from core.browser.session.context import SessionContext
from core.browser.session.launcher import launch_session

logger = logging.getLogger("nexus.browser.session.pool")


class SessionPool:
    """Registry for all active browser sessions. Thread-unsafe by design — asyncio only."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionContext] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> SessionContext:
        """Return an existing or freshly created SessionContext."""
        s_id = session_id or "default"
        if s_id not in self._sessions:
            self._sessions[s_id] = SessionContext(s_id)
        return self._sessions[s_id]

    def has_active_session(self, session_id: Optional[str] = None) -> bool:
        """Return True if the session exists and has an active page."""
        s_id = session_id or "default"
        session = self._sessions.get(s_id)
        if not session:
            return False
        return session._page is not None and not session._page.is_closed()

    async def ensure_page(self, session_id: Optional[str] = None):
        """Return the active Playwright Page, launching the context if needed."""
        session = self.get_or_create(session_id)

        context_is_dead = False
        if session._context:
            try:
                _ = session._context.pages
            except Exception:
                context_is_dead = True

        if not session._page or session._page.is_closed() or context_is_dead:
            # Tear down stale resources before re-launching
            for attr in ("_context", "_playwright"):
                resource = getattr(session, attr, None)
                if resource:
                    try:
                        await resource.close() if attr == "_context" else await resource.stop()
                    except Exception:
                        pass
                    setattr(session, attr, None)

            await launch_session(session)

            # Attach state machine
            if session.state_machine is None:
                from core.browser.state_machine import BrowserStateMachine
                session.state_machine = BrowserStateMachine(session.session_id)

        return session._page

    async def close(self, session_id: Optional[str] = None) -> None:
        s_id = session_id or "default"
        if s_id in self._sessions:
            await self._sessions[s_id].close()
            del self._sessions[s_id]
            logger.info(f"🧹 Closed browser session: {s_id}")

    async def close_all(self) -> None:
        await asyncio.gather(
            *(s.close() for s in self._sessions.values()),
            return_exceptions=True,
        )
        self._sessions.clear()


# Module-level singleton
session_pool = SessionPool()
