"""
browser_context.py
==================
Wraps existing BrowserMemory from browser_session_pool.py.

Design rules:
  - Does NOT re-implement browser tracking. BrowserMemory is already live.
  - Screenshot is TTL-cached (5s) to avoid re-encoding JPEG on every broadcast.
  - Returns safe defaults if no browser session is active.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from core.workspace.workspace_state import BrowserState

logger = logging.getLogger("nexus.workspace.browser")

_TTL_SCREENSHOT = 5.0


class BrowserContext:
    """
    Gathers browser state. Reads from BrowserAgent's existing session memory.
    Consumed only by WorkspaceManager.
    """

    def __init__(self) -> None:
        self._screenshot_cache: Optional[str] = None
        self._screenshot_ts: float = 0.0

    async def collect(self, session_id: Optional[str] = None) -> BrowserState:
        try:
            from core.browser.facade import browser_agent
            session = browser_agent._get_session(session_id)
            mem = session.memory

            screenshot = await self._get_screenshot(browser_agent, session_id)

            return BrowserState(
                current_url=mem.current_url,
                page_title=mem.page_title,
                total_tabs=mem.total_tabs,
                current_tab_index=mem.current_tab_index,
                session_state=mem.session_state,
                last_action=mem.last_action,
                last_action_target=mem.last_action_target,
                step_count=len(mem.step_history),
                screenshot_b64=screenshot,
            )
        except Exception as e:
            logger.debug(f"Browser context collection failed: {e}")
            return BrowserState()

    async def _get_screenshot(self, browser_agent, session_id: Optional[str]) -> Optional[str]:
        now = time.monotonic()
        if self._screenshot_cache and (now - self._screenshot_ts) < _TTL_SCREENSHOT:
            return self._screenshot_cache
        try:
            screenshot = await browser_agent.get_screenshot_base64(session_id)
            self._screenshot_cache = screenshot
            self._screenshot_ts = now
            return screenshot
        except Exception as e:
            logger.debug(f"Screenshot capture failed: {e}")
            return None

    def invalidate_screenshot(self) -> None:
        """Call after any navigation to force screenshot refresh."""
        self._screenshot_cache = None
        self._screenshot_ts = 0.0
