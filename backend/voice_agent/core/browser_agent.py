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
            
        context_is_dead = False
        if self._context:
            try:
                _ = self._context.pages
            except Exception:
                context_is_dead = True

        if not self._page or self._page.is_closed() or context_is_dead:
            # Cleanup old instances if any
            try:
                if self._context:
                    await self._context.close()
            except Exception:
                pass
            try:
                if hasattr(self, "_playwright") and self._playwright:
                    await self._playwright.stop()
            except Exception:
                pass
                
            self._playwright = await async_playwright().start()
            user_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "browser_profile")
            os.makedirs(user_data_dir, exist_ok=True)
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                args=["--no-sandbox"]
            )
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = await self._context.new_page()
        return self._page

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the dedicated browser."""
        try:
            page = await self._ensure_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {"success": True, "verified": True, "result": f"Opened {url} in Nexus dedicated browser."}
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    async def search(self, query: str) -> Dict[str, Any]:
        """Search the web for a query in the dedicated browser."""
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

    async def browser_type(self, selector: str, text: str) -> Dict[str, Any]:
        """
        Type text into a specific element on the active page.
        Clears the field first, then types. Uses triple-click to select-all before typing.
        Execution contract compliant.
        """
        import time
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
            await page.click(selector, timeout=5000)
            await page.click(selector, click_count=3, timeout=5000)
            await page.type(selector, text, delay=30)
            t = f"{time.perf_counter() - start:.2f}s"
            return {
                "success": True,
                "verified": True,
                "execution_time": t,
                "tool": "browser_type",
                "target": selector,
                "error": None,
                "result": f"Typed {len(text)} chars into '{selector}'"
            }
        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_type failed on '{selector}': {e}")
            return {
                "success": False,
                "verified": False,
                "execution_time": t,
                "tool": "browser_type",
                "target": selector,
                "error": str(e)
            }

    async def browser_submit(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit a form. If selector given, tries native form.submit() on that element,
        then falls back to pressing Enter. If no selector, presses Enter on active element.
        """
        import time
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
            submitted = False

            if selector:
                try:
                    # Try native form submission first (most reliable)
                    result = await page.evaluate(
                        f"""(sel) => {{
                            const el = document.querySelector(sel);
                            if (el) {{
                                const form = el.closest('form');
                                if (form) {{ form.submit(); return 'form_submit'; }}
                                el.click(); return 'element_click';
                            }}
                            return 'not_found';
                        }}""",
                        selector
                    )
                    submitted = result in ("form_submit", "element_click")
                except Exception:
                    pass

            if not submitted:
                # Keyboard fallback — works on search bars, login fields, etc.
                await page.keyboard.press("Enter")
                submitted = True

            t = f"{time.perf_counter() - start:.2f}s"
            return {
                "success": submitted,
                "verified": submitted,
                "execution_time": t,
                "tool": "browser_submit",
                "target": selector or "active_element",
                "error": None
            }
        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_submit failed: {e}")
            return {
                "success": False,
                "verified": False,
                "execution_time": t,
                "tool": "browser_submit",
                "target": selector or "active_element",
                "error": str(e)
            }

    async def browser_tab_management(self, action: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Manage browser tabs.
        Actions:
          - 'new'    : open a new blank tab (optionally navigate to target URL)
          - 'close'  : close the current active tab
          - 'switch' : switch to tab by index (target='0','1',...) or by partial title match
          - 'list'   : return all open tab titles
        """
        import time
        start = time.perf_counter()
        try:
            # Ensure context is alive
            await self._ensure_page()
            ctx = self._context
            assert ctx is not None, "Browser context not initialized"
            pages = ctx.pages

            if action == "new":
                new_page = await ctx.new_page()
                self._page = new_page
                if target:
                    await new_page.goto(target, wait_until="domcontentloaded", timeout=15000)
                t = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": True, "verified": True,
                    "execution_time": t, "tool": "browser_tab_management",
                    "target": target or "blank", "error": None,
                    "result": f"Opened new tab. URL: {target or 'about:blank'}"
                }

            elif action == "close":
                if self._page and not self._page.is_closed():
                    await self._page.close()
                    # Switch to last remaining tab
                    remaining = [p for p in ctx.pages if not p.is_closed()]
                    self._page = remaining[-1] if remaining else await ctx.new_page()
                t = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": True, "verified": True,
                    "execution_time": t, "tool": "browser_tab_management",
                    "target": "current_tab", "error": None,
                    "result": f"Closed tab. {len(ctx.pages)} tab(s) remaining."
                }

            elif action == "switch":
                switched = False
                if target is not None:
                    # Index-based switch
                    if target.isdigit():
                        idx = int(target)
                        if 0 <= idx < len(pages):
                            self._page = pages[idx]
                            await self._page.bring_to_front()
                            switched = True
                    else:
                        # Title-based switch (fuzzy)
                        from rapidfuzz import fuzz, process as rfp
                        titles = [p.url + " " + (await p.title()) for p in pages]
                        best = rfp.extractOne(target, titles, scorer=fuzz.token_set_ratio, score_cutoff=50)
                        if best:
                            idx = titles.index(best[0])
                            self._page = pages[idx]
                            await self._page.bring_to_front()
                            switched = True

                t = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": switched, "verified": switched,
                    "execution_time": t, "tool": "browser_tab_management",
                    "target": target, "error": None if switched else "Tab not found"
                }

            elif action == "list":
                tab_info = []
                for i, p in enumerate(pages):
                    try:
                        title = await p.title()
                    except Exception:
                        title = "(loading)"
                    tab_info.append(f"[{i}] {title} — {p.url}")
                t = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": True, "verified": True,
                    "execution_time": t, "tool": "browser_tab_management",
                    "target": "all_tabs", "error": None,
                    "result": tab_info
                }

            else:
                t = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": False, "verified": False,
                    "execution_time": t, "tool": "browser_tab_management",
                    "target": action, "error": f"Unknown action: '{action}'. Use new/close/switch/list."
                }

        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_tab_management failed: {e}")
            return {
                "success": False, "verified": False,
                "execution_time": t, "tool": "browser_tab_management",
                "target": action, "error": str(e)
            }

    async def get_screenshot_base64(self) -> Optional[str]:
        try:
            if not self._page or self._page.is_closed():
                return None
            import base64
            # Keep quality low (50) for fast transmission and lower payload size
            img_bytes = await self._page.screenshot(type="jpeg", quality=50)
            return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to capture browser screenshot: {e}")
            return None

    async def close(self) -> None:
        """Close the browser instance and clean up Playwright resources."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context:
                await self._context.close()
            if hasattr(self, "_playwright") and self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close BrowserAgent: {e}")
        finally:
            self._page = None
            self._context = None

browser_agent = BrowserAgent()
