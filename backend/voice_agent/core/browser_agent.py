import logging
import asyncio
import os
from typing import Dict, Any, Optional

logger = logging.getLogger("nexus.browser_agent")

class BrowserAgent:
    """
    Model-agnostic Browser capabilities. 
    Rule 5: Any model can use open_url, click, search, extract, screenshot.
    """
    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        
    async def _ensure_page(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright is not installed. Please install playwright to use advanced browser capabilities.")
            
        if not self._page:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=False) # Headless=False so user sees the action
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
        return self._page

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the browser."""
        # Fast path: use default OS browser if we just want to open
        # But if we want to retain control for click/extract, we use Playwright
        try:
            import webbrowser
            webbrowser.open(url)
            return {"success": True, "verified": True, "result": f"Opened {url} in default browser."}
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

    async def search(self, query: str) -> Dict[str, Any]:
        """Search the web for a query."""
        import urllib.parse
        encoded = urllib.parse.quote(query)
        return await self.open_url(f"https://duckduckgo.com/?q={encoded}")

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element on the currently controlled Playwright page."""
        try:
            page = await self._ensure_page()
            await page.click(selector, timeout=5000)
            return {"success": True, "verified": True, "result": f"Clicked '{selector}'"}
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    async def extract(self, url: str) -> Dict[str, Any]:
        """Extract visible text from a URL for RAG/Processing."""
        try:
            page = await self._ensure_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            text = await page.evaluate("document.body.innerText")
            return {"success": True, "verified": True, "result": text[:5000]} # Limit extraction size
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

    async def screenshot(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page, or navigate to a URL first."""
        try:
            page = await self._ensure_page()
            if url:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                
            path = os.path.join(os.path.expanduser("~"), "nexus_screenshot.png")
            await page.screenshot(path=path)
            return {"success": True, "verified": True, "result": f"Screenshot saved to {path}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

browser_agent = BrowserAgent()
