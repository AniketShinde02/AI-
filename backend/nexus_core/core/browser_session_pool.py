# browser_session_pool.py
# ======================
# Responsibility: Isolated Playwright browser contexts pool and session profiles directory tracking.

import os
import time
import shutil
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("nexus.browser_session_pool")

@dataclass
class BrowserMemory:
    current_url: str = "about:blank"
    page_title: str = ""
    current_tab_index: int = 0
    total_tabs: int = 1
    last_action: str = ""
    last_action_target: str = ""
    last_action_result: str = ""
    session_state: str = "idle"   # idle | navigating | interacting | completed | error
    step_history: List[Dict[str, Any]] = field(default_factory=list)

    def record_step(self, action: str, target: str, result: str, success: bool):
        self.last_action = action
        self.last_action_target = target
        self.last_action_result = result
        self.step_history.append({
            "action": action,
            "target": target,
            "result": result[:200],
            "success": success,
            "timestamp": time.time(),
        })
        # Keep last 20 steps
        if len(self.step_history) > 20:
            self.step_history = self.step_history[-20:]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Don't send full history over WS — too large
        d["step_count"] = len(d.pop("step_history", []))
        return d


class SessionContext:
    """Encapsulates isolated resources and memory state for a single browser connection connection."""
    _page: Any
    _context: Any
    _playwright: Any

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._page = None
        self._context = None
        self._playwright = None
        self.memory = BrowserMemory()

    async def close(self) -> None:
        """Clean up local Playwright resources and profile directory."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._playwright = None
        self.memory.session_state = "idle"

        user_data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", f"browser_profile_{self.session_id}"
        )
        if os.path.exists(user_data_dir):
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to remove browser profile directory {user_data_dir}: {e}")
                
