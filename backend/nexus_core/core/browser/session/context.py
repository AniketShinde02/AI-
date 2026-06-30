"""
browser/session/context.py
===========================
Nexus Browser Domain — Session Context

Single Responsibility: Manages the lifecycle of a single isolated Playwright
browser context (launch, persist, teardown, profile directory management).
"""
from __future__ import annotations

import logging
import os
import shutil
from typing import Any, Optional

from core.browser.models import BrowserMemory

logger = logging.getLogger("nexus.browser.session")


class SessionContext:
    """
    Encapsulates one isolated Playwright browser context per session_id.

    Profile directories are isolated from the user's real browser.
    Profiles prefixed with 'user_' survive session close (login persistence).
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._page: Any = None
        self._context: Any = None
        self._playwright: Any = None
        self.memory = BrowserMemory()
        self.state_machine: Any = None  # Injected by _ensure_page

    @property
    def profile_dir(self) -> str:
        """Absolute path to this session's isolated browser profile directory."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", f"browser_profile_{self.session_id}"
        )

    async def close(self) -> None:
        """Tear down Playwright resources. Preserves profile for 'user_' sessions."""
        for resource, name in [(self._page, "page"), (self._context, "context"), (self._playwright, "playwright")]:
            if resource is None:
                continue
            try:
                if name == "page" and not resource.is_closed():
                    await resource.close()
                elif name == "context":
                    await resource.close()
                elif name == "playwright":
                    await resource.stop()
            except Exception:
                pass

        self._page = None
        self._context = None
        self._playwright = None
        self.memory.session_state = "idle"

        if os.path.exists(self.profile_dir) and not self.session_id.startswith("user_"):
            try:
                shutil.rmtree(self.profile_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to remove profile {self.profile_dir}: {e}")
        elif self.session_id.startswith("user_"):
            logger.info(f"Preserved persistent profile for session: {self.session_id}")
