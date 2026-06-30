"""
browser/resiliency/locator.py
==============================
Nexus Browser Domain — 7-Level Locator Cascade

Single Responsibility: Resolve web elements using a cascading fallback strategy
across ARIA roles, labels, placeholders, text, test-IDs, CSS, and XPath — including
full iframe and shadow DOM penetration.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("nexus.browser.resiliency.locator")

_TIMEOUT = 3000  # ms per locator level


class LocatorNotFoundError(Exception):
    pass


class LocatorEngine:
    """
    7-level element location cascade with iframe + shadow DOM support.

    Level 1: ARIA role + name
    Level 2: aria-label text
    Level 3: placeholder text
    Level 4: visible text content
    Level 5: data-testid attribute
    Level 6: CSS selector
    Level 7: XPath expression
    """

    async def locate(self, page: Any, selector: str, timeout: int = _TIMEOUT) -> Any:
        """Return a Playwright Locator for `selector`, or raise LocatorNotFoundError."""
        strategies = self._build_strategies(selector)

        all_frames = [page] + list(page.frames)

        for frame in all_frames:
            for level, locator_expr in enumerate(strategies, start=1):
                try:
                    loc = frame.locator(locator_expr)
                    await loc.first.wait_for(state="visible", timeout=timeout)
                    logger.debug(f"[Locator] Level {level} matched: {locator_expr!r}")
                    return loc.first
                except Exception:
                    continue

        raise LocatorNotFoundError(
            f"All 7 locator levels + {len(all_frames)} frames exhausted for: {selector!r}"
        )

    async def click_element(self, page: Any, selector: str, timeout: int = _TIMEOUT) -> bool:
        try:
            loc = await self.locate(page, selector, timeout)
            await loc.click(force=True, timeout=timeout)
            return True
        except LocatorNotFoundError:
            return False

    async def fill_element(self, page: Any, selector: str, text: str, timeout: int = _TIMEOUT) -> bool:
        try:
            loc = await self.locate(page, selector, timeout)
            await loc.fill(text, timeout=timeout)
            return True
        except LocatorNotFoundError:
            return False

    def _build_strategies(self, selector: str) -> list:
        return [
            f"[role][aria-label='{selector}']",
            f"[aria-label='{selector}']",
            f"[placeholder='{selector}']",
            f"text={selector}",
            f"[data-testid='{selector}']",
            selector,  # raw CSS
            f"xpath=//*[contains(text(), '{selector}')]",
        ]


locator_engine = LocatorEngine()
