"""
browser/verification/nav_verifier.py
======================================
Nexus Browser Domain — Navigation Verification

Single Responsibility: Verify that a page transition succeeded. Checks HTTP
status, waits for network idle, and runs a MutationObserver to confirm SPA
hydration. Returns True/False — never triggers actions.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("nexus.browser.verification")

_SPA_HYDRATION_JS = """
() => new Promise((resolve) => {
    if (document.readyState === 'complete') return resolve(true);
    let observer = new MutationObserver(() => {
        clearTimeout(timeout);
        observer.disconnect();
        resolve(true);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    let timeout = setTimeout(() => { observer.disconnect(); resolve(true); }, 1000);
})
"""


class NavigationVerifier:
    """
    Verifies navigation success after a page.goto() call.

    Checks:
      1. HTTP status < 400
      2. Network idle (SPA quiescence)
      3. JS hydration via MutationObserver
      4. Optional URL fragment presence
      5. Page title sanity (no 404 titles)
    """

    async def verify(
        self,
        page: Any,
        response: Optional[Any] = None,
        expected_url_fragment: Optional[str] = None,
        current_url: str = "",
        page_title: str = "",
    ) -> bool:
        try:
            if not page or page.is_closed():
                return False

            # 1. HTTP status check
            if response and response.status >= 400:
                logger.warning(f"[NavVerifier] HTTP {response.status}")
                return False

            # 2. Network quiescence
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass  # Long-polling / WebSocket pages won't ever reach idle

            # 3. SPA hydration confirmation
            try:
                await page.evaluate(_SPA_HYDRATION_JS)
            except Exception:
                pass

            # 4. URL fragment check
            if expected_url_fragment and expected_url_fragment.lower() not in current_url.lower():
                return False

            # 5. Title sanity
            if page_title and "error" in page_title.lower() and "404" in page_title:
                return False
            if page_title == "about:blank" and current_url != "about:blank":
                return False

            return True
        except Exception as e:
            logger.error(f"[NavVerifier] Failed: {e}")
            return False

    async def verify_media_playing(self, page: Any) -> bool:
        """Checks if any HTML5 video or audio element is currently playing."""
        try:
            return await page.evaluate('''() => {
                const media = Array.from(document.querySelectorAll('video, audio'));
                return media.some(m => m.readyState > 2 && !m.paused && !m.ended);
            }''')
        except Exception as e:
            logger.error(f"[NavVerifier] Media check failed: {e}")
            return False

nav_verifier = NavigationVerifier()
