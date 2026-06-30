"""
browser_locator.py
==================
Nexus BrowserAgent V1.1 — 7-Level Locator Cascade

Priority order (highest to lowest):
  1. ARIA role + accessible name
  2. Accessible label
  3. Placeholder text
  4. Visible text
  5. Stable test ID (data-testid, data-qa, data-cy)
  6. CSS selector
  7. XPath (last resort)

Each level times out independently (3s) before falling to the next.
Returns the Playwright Locator that matched, or raises LocatorNotFoundError.
"""
import logging
import asyncio
from typing import Optional, Any

logger = logging.getLogger("nexus.browser_locator")


class LocatorNotFoundError(Exception):
    """Raised when no locator strategy could find the element."""
    pass


class LocatorEngine:
    """
    Attempts to locate a web element using a 7-level priority cascade.
    All strategies are tried in order; the first match wins.
    """

    async def locate(
        self,
        page: Any,
        target: str,
        role: Optional[str] = None,
        timeout: int = 3000,
    ) -> Any:
        """
        Locate an element using the full cascade.

        Args:
            page: Playwright Page object
            target: The target string (accessible name, text, CSS selector, etc.)
            role: Optional ARIA role hint (e.g. "button", "textbox", "link")
            timeout: Per-strategy timeout in ms

        Returns:
            Playwright Locator pointing to the matched element

        Raises:
            LocatorNotFoundError if all strategies fail
        """
        frames = getattr(page, 'frames', [page])
        last_err = None
        
        for frame in frames:
            strategies = [
                ("ARIA Role", lambda f=frame: self._by_aria(f, target, role, timeout)),
                ("Label", lambda f=frame: self._by_label(f, target, timeout)),
                ("Placeholder", lambda f=frame: self._by_placeholder(f, target, timeout)),
                ("Text", lambda f=frame: self._by_text(f, target, timeout)),
                ("Test ID", lambda f=frame: self._by_test_id(f, target, timeout)),
                ("CSS", lambda f=frame: self._by_css(f, target, timeout)),
                ("XPath", lambda f=frame: self._by_xpath(f, target, timeout)),
            ]

            for name, strategy in strategies:
                try:
                    locator = await strategy()
                    if locator:
                        logger.debug(f"[Locator] ✅ Strategy '{name}' matched for target: {target!r} in frame {frame.name}")
                        return locator
                except Exception as e:
                    last_err = e
                    continue

        raise LocatorNotFoundError(
            f"All 7 locator strategies failed across {len(frames)} frames for target: {target!r}. Last error: {last_err}"
        )

    async def _by_aria(self, page: Any, target: str, role: Optional[str], timeout: int) -> Optional[Any]:
        """Level 1: ARIA role + accessible name."""
        # Try with explicit role first
        if role:
            loc = page.get_by_role(role, name=target)
            if await loc.count() > 0:
                await loc.first.wait_for(state="visible", timeout=timeout)
                return loc.first

        # Try common roles without explicit role hint
        for r in ["textbox", "searchbox", "button", "link", "combobox", "listbox"]:
            try:
                loc = page.get_by_role(r, name=target)
                if await loc.count() > 0:
                    await loc.first.wait_for(state="attached", timeout=timeout)
                    return loc.first
            except Exception:
                continue
        return None

    async def _by_label(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 2: Element associated with a <label>."""
        loc = page.get_by_label(target)
        if await loc.count() > 0:
            await loc.first.wait_for(state="attached", timeout=timeout)
            return loc.first
        return None

    async def _by_placeholder(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 3: Input with matching placeholder."""
        loc = page.get_by_placeholder(target)
        if await loc.count() > 0:
            await loc.first.wait_for(state="attached", timeout=timeout)
            return loc.first
        return None

    async def _by_text(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 4: Visible text content."""
        # Exact match first
        loc = page.get_by_text(target, exact=True)
        if await loc.count() > 0:
            await loc.first.wait_for(state="visible", timeout=timeout)
            return loc.first
        # Partial match
        loc = page.get_by_text(target, exact=False)
        if await loc.count() > 0:
            await loc.first.wait_for(state="visible", timeout=timeout)
            return loc.first
        return None

    async def _by_test_id(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 5: Stable test IDs (data-testid, data-qa, data-cy)."""
        for attr in ["data-testid", "data-qa", "data-cy", "data-test"]:
            try:
                loc = page.locator(f"[{attr}='{target}']")
                if await loc.count() > 0:
                    await loc.first.wait_for(state="attached", timeout=timeout)
                    return loc.first
            except Exception:
                continue
        return None

    async def _by_css(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 6: CSS selector."""
        # Only attempt if target looks like a selector (has # . [ : or is a tag)
        if not any(c in target for c in ["#", ".", "[", ":", " ", ">"]):
            # Bare word — not a CSS selector, skip
            return None
        loc = page.locator(target)
        if await loc.count() > 0:
            await loc.first.wait_for(state="attached", timeout=timeout)
            return loc.first
        return None

    async def _by_xpath(self, page: Any, target: str, timeout: int) -> Optional[Any]:
        """Level 7: XPath (last resort)."""
        # Try direct xpath if target starts with //
        if target.startswith("//") or target.startswith("(//"):
            loc = page.locator(f"xpath={target}")
            if await loc.count() > 0:
                await loc.first.wait_for(state="attached", timeout=timeout)
                return loc.first

        # Build a smart xpath searching for visible text or id/name attributes
        xpath_attempts = [
            f"xpath=//*[@id='{target}']",
            f"xpath=//*[@name='{target}']",
            f"xpath=//*[@aria-label='{target}']",
            f"xpath=//*[contains(text(), '{target}')]",
            f"xpath=//*[contains(@placeholder, '{target}')]",
        ]
        for xpath in xpath_attempts:
            try:
                loc = page.locator(xpath)
                if await loc.count() > 0:
                    await loc.first.wait_for(state="attached", timeout=timeout)
                    return loc.first
            except Exception:
                continue
        return None

    async def fill_element(
        self,
        page: Any,
        target: str,
        text: str,
        role: Optional[str] = None,
        timeout: int = 5000,
    ) -> bool:
        """
        Locate and fill an input element. Returns True on success.
        Tries fill(force=True) first, then keyboard input as fallback.
        """
        locator = await self.locate(page, target, role=role or "textbox", timeout=timeout)

        # Try fill first (most reliable for inputs)
        try:
            await locator.fill(text, force=True, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"[Locator] fill() failed: {e}, trying keyboard")

        # Keyboard fallback
        try:
            await locator.click(force=True, timeout=timeout)
            await locator.press("Control+A")
            await locator.press("Backspace")
            await locator.type(text, delay=30)
            return True
        except Exception as e:
            logger.error(f"[Locator] Keyboard fill also failed: {e}")
            return False

    async def click_element(
        self,
        page: Any,
        target: str,
        role: Optional[str] = None,
        timeout: int = 5000,
    ) -> bool:
        """
        Locate and click an element. Returns True on success.
        """
        locator = await self.locate(page, target, role=role, timeout=timeout)
        try:
            await locator.click(force=True, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"[Locator] click() failed: {e}")
            return False


locator_engine = LocatorEngine()
