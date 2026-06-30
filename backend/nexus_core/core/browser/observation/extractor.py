"""
browser/observation/extractor.py
==================================
Nexus Browser Domain — DOM & A11y Observation

Single Responsibility: Extract structured page data (DOM snapshot, accessibility
tree, raw text, screenshot) from the active Playwright page. Zero action logic.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional

# Injected JS comes from the prompts subpackage (pure data, no logic)
from core.browser.prompts.scripts import DOM_SNAPSHOT_JS, A11Y_TREE_JS

logger = logging.getLogger("nexus.browser.observation")


class PageExtractor:
    """Stateless extractor — every method is a pure read from the Playwright page."""

    async def dom_snapshot(self, page: Any) -> Dict[str, Any]:
        """Extract visible text, buttons, inputs, and links from the live DOM."""
        try:
            result = await page.evaluate(DOM_SNAPSHOT_JS)
            return {"success": True, "verified": True, "result": result}
        except Exception as e:
            logger.error(f"DOM snapshot failed: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    async def a11y_tree(self, page: Any) -> Dict[str, Any]:
        """Extract the accessibility tree with roles, labels, and coordinates."""
        try:
            tree = await page.evaluate(A11Y_TREE_JS)
            return {"success": True, "verified": True, "result": tree}
        except Exception as e:
            logger.error(f"A11y tree failed: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    async def screenshot_b64(self, page: Any, quality: int = 50) -> Optional[str]:
        """Return a base64-encoded JPEG screenshot, or None on failure."""
        try:
            if not page or page.is_closed():
                return None
            img_bytes = await page.screenshot(type="jpeg", quality=quality)
            return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    async def page_text(self, page: Any, max_chars: int = 5000) -> str:
        """Return raw visible text from document.body.innerText."""
        try:
            return (await page.evaluate("document.body.innerText"))[:max_chars]
        except Exception:
            return ""

    async def text_present(self, page: Any, text: str) -> bool:
        """Return True if `text` is visible anywhere on the page (case-insensitive)."""
        try:
            return bool(await page.evaluate(
                "(t) => document.body.innerText.toLowerCase().includes(t.toLowerCase())", text
            ))
        except Exception:
            return False

    async def check_media_status(self, page: Any) -> Dict[str, Any]:
        """Return status of playing audio/video on the page."""
        try:
            return await page.evaluate('''() => {
                const media = Array.from(document.querySelectorAll('video, audio'));
                const playing = media.filter(m => !m.paused && !m.ended && m.readyState > 2);
                return {
                    has_media: media.length > 0,
                    is_playing: playing.length > 0,
                    media_types: media.map(m => m.tagName.toLowerCase())
                };
            }''')
        except Exception as e:
            logger.debug(f"Media status check failed: {e}")
            return {"has_media": False, "is_playing": False, "media_types": []}


# Module-level singleton
page_extractor = PageExtractor()
