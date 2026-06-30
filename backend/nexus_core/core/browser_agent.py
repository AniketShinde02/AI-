"""
browser_agent.py
================
Browser Agent V1 — Nexus Stonic/Hermes-inspired implementation.

Capabilities:
  1. DOM Snapshot Extraction     — visible text, buttons, inputs, links
  2. Accessibility Tree Snapshot — role, label, coordinates, element id
  3. Screenshot Capture          — base64 JPEG, used when DOM is insufficient
  4. Observe-Decide-Execute-Verify loop — every action is verified before continuing
  5. Goal-oriented Task Execution (Phase C) — run_browser_task()
  6. Browser Memory (Phase D) — tracks current_url, tab, last_action, page_title, session_state

Phase E: Isolated Playwright profile (data/browser_profile_<session_id>) — never touches user Chrome.
"""
import logging
import asyncio
import json
import os
import time
import base64
import shutil
from typing import Dict, Any, Optional, List

from core.browser_stealth import _DOM_SNAPSHOT_JS, _A11Y_TREE_JS, _STEALTH_JS
from core.browser_session_pool import BrowserMemory, SessionContext

logger = logging.getLogger("nexus.browser_agent")


class BrowserAgent:
    """
    Browser Agent V1 — Observe-Decide-Execute-Verify loop with DOM/A11y snapshots.
    Supports session-isolated contexts (SessionContext) mapped by session_id.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}

    def _get_session(self, session_id: Optional[str] = None) -> SessionContext:
        s_id = session_id or "default"
        if s_id not in self._sessions:
            self._sessions[s_id] = SessionContext(s_id)
        return self._sessions[s_id]

    # ---------------------------------------------------------------------------
    # Isolated context management
    # ---------------------------------------------------------------------------

    async def _ensure_page(self, session_id: Optional[str] = None):
        session = self._get_session(session_id)
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        from core.browser_launcher import resolve_browser

        context_is_dead = False
        if session._context:
            try:
                _ = session._context.pages
            except Exception:
                context_is_dead = True

        if not session._page or session._page.is_closed() or context_is_dead:
            # Clean up stale instances
            try:
                if session._context:
                    await session._context.close()
            except Exception:
                pass
            try:
                if session._playwright:
                    await session._playwright.stop()
            except Exception:
                pass

            # Resolve system browser — no hardcoded paths
            browser_hint = session.memory.browser_hint  # e.g. "brave", "chrome", set by caller
            exe_path, channel, is_fallback = resolve_browser(user_hint=browser_hint)
            if is_fallback:
                logger.warning(f"[BrowserAgent] Using fallback browser (bundled Chromium)")

            session._playwright = await async_playwright().start()
            # Profile is isolated per session_id (never touches user's real browser profile)
            user_data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", f"browser_profile_{session.session_id}"
            )
            os.makedirs(user_data_dir, exist_ok=True)

            launch_kwargs = dict(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1280,720",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            if exe_path:
                launch_kwargs["executable_path"] = exe_path

            browser_driver = getattr(session._playwright, channel, session._playwright.chromium)
            session._context = await browser_driver.launch_persistent_context(
                user_data_dir, **launch_kwargs
            )
            await session._context.add_init_script(_STEALTH_JS)

            if session._context.pages:
                session._page = session._context.pages[0]
            else:
                session._page = await session._context.new_page()

            try:
                from core.database import db
                db_session = await db.get_browser_session(session.session_id)
                if db_session:
                    session.memory.current_url = db_session["current_url"]
                    session.memory.page_title = db_session["page_title"]
                    session.memory.last_action = db_session["last_action"]
                    session.memory.session_state = db_session["session_state"]
            except Exception as e:
                logger.debug(f"DB Hydration failed: {e}")

        return session._page

    async def _update_memory_from_page(self, session_id: Optional[str] = None):
        """Sync BrowserMemory with current page state."""
        session = self._get_session(session_id)
        try:
            if not session._page or session._page.is_closed():
                return
            session.memory.current_url = session._page.url
            session.memory.page_title = await session._page.title()
            if session._context:
                pages = session._context.pages
                session.memory.total_tabs = len(pages)
                try:
                    session.memory.current_tab_index = pages.index(session._page)
                except ValueError:
                    session.memory.current_tab_index = 0
        except Exception as e:
            logger.debug(f"Memory sync failed for session {session_id}: {e}")

        try:
            from core.database import db
            asyncio.create_task(db.upsert_browser_session(
                session_id=session.session_id,
                current_url=session.memory.current_url,
                page_title=session.memory.page_title,
                last_action=session.memory.last_action,
                tab_count=session.memory.total_tabs,
                session_state=session.memory.session_state
            ))
        except Exception as e:
            logger.debug(f"DB sync failed: {e}")

    def get_workspace_state(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Return browser memory as a workspace state dict."""
        session = self._get_session(session_id)
        return session.memory.to_dict()

    # ---------------------------------------------------------------------------
    # Phase 1: DOM Snapshot
    # ---------------------------------------------------------------------------

    async def get_dom_snapshot(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract visible DOM elements: text, buttons, inputs, links."""
        try:
            page = await self._ensure_page(session_id)
            result = await page.evaluate(_DOM_SNAPSHOT_JS)
            return {"success": True, "verified": True, "result": result}
        except Exception as e:
            logger.error(f"DOM snapshot failed for session {session_id}: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    # ---------------------------------------------------------------------------
    # Phase 2: Accessibility Tree
    # ---------------------------------------------------------------------------

    async def get_accessibility_tree(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract accessibility tree with role, label, coordinates."""
        try:
            page = await self._ensure_page(session_id)
            tree = await page.evaluate(_A11Y_TREE_JS)
            return {"success": True, "verified": True, "result": tree}
        except Exception as e:
            logger.error(f"A11y tree failed for session {session_id}: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    # ---------------------------------------------------------------------------
    # Phase 3: Screenshot Capture (used only when DOM is insufficient)
    # ---------------------------------------------------------------------------

    async def get_screenshot_base64(self, session_id: Optional[str] = None) -> Optional[str]:
        """Get current page screenshot as base64 JPEG (low quality for fast WS transport)."""
        session = self._get_session(session_id)
        try:
            if not session._page or session._page.is_closed():
                return None
            img_bytes = await session._page.screenshot(type="jpeg", quality=50)
            return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Screenshot capture failed for session {session_id}: {e}")
            return None

    async def screenshot(self, url: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot, optionally navigating first."""
        session = self._get_session(session_id)
        try:
            page = await self._ensure_page(session_id)
            if url:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            path = os.path.join(os.path.expanduser("~"), f"nexus_screenshot_{session.session_id}.png")
            await page.screenshot(path=path)
            
            img_bytes = await page.screenshot(type="jpeg", quality=60)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            
            try:
                from core.vision_parser import vision_parser
                analysis = await vision_parser.analyze_screenshot(
                    img_b64, 
                    prompt="Describe the current webpage concisely. What UI elements are visible?",
                    use_som=False
                )
            except Exception as e:
                analysis = f"Vision failed: {e}"

            await self._update_memory_from_page(session_id)
            return {"success": True, "verified": True, "result": f"Screenshot saved to {path} | Vision: {analysis}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}
    async def download(self, url: str, dest: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        try:
            page = await self._ensure_page(session_id)
            async with page.expect_download(timeout=30000) as download_info:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            dl = await download_info.value
            await dl.save_as(dest)
            return {"success": True, "verified": True, "result": f"Downloaded to {dest}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": f"Download failed: {e}"}

    async def upload(self, selector: str, file_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        try:
            page = await self._ensure_page(session_id)
            if not os.path.exists(file_path):
                return {"success": False, "verified": False, "error": f"File not found: {file_path}"}
            await page.set_input_files(selector, file_path, timeout=10000)
            return {"success": True, "verified": True, "result": f"Uploaded {file_path} to {selector}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": f"Upload failed: {e}"}
    # ---------------------------------------------------------------------------
    # Phase 4: Observe-Decide-Execute-Verify helpers
    # ---------------------------------------------------------------------------

    async def observe(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Observe the current page state."""
        session = self._get_session(session_id)
        dom = await self.get_dom_snapshot(session_id)
        await self._update_memory_from_page(session_id)
        return {
            "success": True,
            "verified": True,
            "url": session.memory.current_url,
            "title": session.memory.page_title,
            "dom": dom.get("result", {}),
            "memory": session.memory.to_dict(),
        }

    async def _verify_navigation(self, expected_url_fragment: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """Verify navigation succeeded."""
        session = self._get_session(session_id)
        try:
            await asyncio.sleep(0.5)
            await self._update_memory_from_page(session_id)
            if expected_url_fragment and expected_url_fragment.lower() in session.memory.current_url.lower():
                return True
            if session.memory.page_title and session.memory.page_title != "about:blank":
                return True
            return False
        except Exception:
            return False

    async def _verify_element_visible(self, selector: str, session_id: Optional[str] = None) -> bool:
        """Verify an element exists and is visible."""
        session = self._get_session(session_id)
        try:
            if not session._page or session._page.is_closed():
                return False
            el = await session._page.query_selector(selector)
            if el:
                return await el.is_visible()
            return False
        except Exception:
            return False

    # ---------------------------------------------------------------------------
    # Core navigation + interaction
    # ---------------------------------------------------------------------------

    async def open_url(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to URL and verify success."""
        import random
        # IP Pressure Tracking Mitigation: Random delay before new navigations
        await asyncio.sleep(random.uniform(1.5, 3.5))

        session = self._get_session(session_id)
        start = time.perf_counter()
        try:
            page = await self._ensure_page(session_id)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Transparent 429 Handling
            if response and response.status == 429:
                logger.warning(f"⚠️ [Rate Limit] 429 encountered on {url}. Triggering delay.")
                await asyncio.sleep(random.uniform(5.0, 10.0))
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            await self._update_memory_from_page(session_id)
            verified = await self._verify_navigation(url.split("//")[-1].split("/")[0], session_id)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("open_url", url, f"Navigated to {session.memory.page_title}", verified)
            session.memory.session_state = "navigating"
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_open_url",
                "target": url, "error": None,
                "result": f"Opened '{session.memory.page_title}' ({session.memory.current_url})"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"open_url failed for {url} on session {session_id}: {e}")
            session.memory.record_step("open_url", url, str(e), False)
            session.memory.session_state = "error"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_open_url", "target": url, "error": str(e)}

    async def search(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Context-aware search.
        
        If the current page has a known search shortcut (YouTube: /, GitHub: /),
        uses the page's native search bar. Otherwise falls back to DuckDuckGo.
        """
        import urllib.parse
        session = self._get_session(session_id)
        current_url = session.memory.current_url or "about:blank"

        # Context-aware: use the current site's own search
        PAGE_SEARCH_SHORTCUTS = {
            "youtube.com": "https://www.youtube.com/results?search_query={q}",
            "github.com": "https://github.com/search?q={q}",
            "amazon.com": "https://www.amazon.com/s?k={q}",
            "wikipedia.org": "https://en.wikipedia.org/wiki/Special:Search?search={q}",
            "reddit.com": "https://www.reddit.com/search/?q={q}",
        }
        encoded = urllib.parse.quote(query)
        for domain, pattern in PAGE_SEARCH_SHORTCUTS.items():
            if domain in current_url:
                url = pattern.format(q=encoded)
                logger.info(f"[Search] Context-aware → {url}")
                return await self.open_url(url, session_id)

        # Default: DuckDuckGo (no tracking, no rate limits)
        url = f"https://duckduckgo.com/?q={encoded}"
        logger.info(f"[Search] DuckDuckGo → {url}")
        return await self.open_url(url, session_id)

    async def click(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Click an element and verify."""
        session = self._get_session(session_id)
        start = time.perf_counter()
        try:
            page = await self._ensure_page(session_id)
            url_before = page.url
            
            # Selector Recovery / Self-Healing strategy
            clicked = False
            fallbacks = [
                selector,
                f"text='{selector}'",
                f"text={selector}",
                f"xpath=//*[contains(text(), '{selector}')]",
                f"xpath=//*[@aria-label='{selector}']"
            ]
            
            last_err = None
            for f in fallbacks:
                try:
                    await page.click(f, timeout=3000)
                    clicked = True
                    break
                except Exception as e:
                    last_err = e
            
            if not clicked:
                raise last_err or Exception("All click strategies failed.")
                
            await asyncio.sleep(0.5)
            await self._update_memory_from_page(session_id)
            url_changed = page.url != url_before
            verified = url_changed or bool(session.memory.page_title)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("click", selector, f"Clicked. URL changed: {url_changed}", verified)
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_click",
                "target": selector, "error": None,
                "result": f"Clicked '{selector}'. Page: {session.memory.page_title}"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"click failed on {selector} for session {session_id}: {e}")
            session.memory.record_step("click", selector, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_click", "target": selector, "error": str(e)}

    async def extract(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to URL and extract text."""
        try:
            page = await self._ensure_page(session_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._update_memory_from_page(session_id)
            text = await page.evaluate("document.body.innerText")
            return {
                "success": True, "verified": True,
                "tool": "browser_extract", "target": url,
                "result": text[:5000]
            }
        except Exception as e:
            return {"success": False, "verified": False, "tool": "browser_extract",
                    "target": url, "error": str(e)}

    async def download(self, url: str, dest: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Download a file from a URL to a local destination."""
        start = time.perf_counter()
        try:
            page = await self._ensure_page(session_id)
            async with page.expect_download() as download_info:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            download = await download_info.value
            await download.save_as(dest)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {
                "success": True, "verified": True, "execution_time": elapsed,
                "tool": "browser_download", "target": dest, "error": None,
                "result": f"Downloaded to '{dest}'"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed, "tool": "browser_download", "target": dest, "error": str(e)}

    async def upload(self, selector: str, file_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload a local file to a specific file input element."""
        start = time.perf_counter()
        try:
            import os
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File '{file_path}' not found.")
            
            page = await self._ensure_page(session_id)
            await page.set_input_files(selector, file_path, timeout=8000)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {
                "success": True, "verified": True, "execution_time": elapsed,
                "tool": "browser_upload", "target": selector, "error": None,
                "result": f"Uploaded '{file_path}' to '{selector}'"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed, "tool": "browser_upload", "target": selector, "error": str(e)}

    async def browser_type(self, selector: str, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Type text into a field using the 7-level LocatorEngine cascade."""
        from core.browser_locator import locator_engine, LocatorNotFoundError
        session = self._get_session(session_id)
        start = time.perf_counter()
        try:
            page = await self._ensure_page(session_id)
            filled = await locator_engine.fill_element(page, selector, text, timeout=5000)
            if not filled:
                raise Exception(f"LocatorEngine could not fill '{selector}'")

            # Verify value was set
            try:
                value = await page.evaluate(
                    "(sel) => { const el = document.querySelector(sel); return el ? (el.value || el.textContent) : ''; }",
                    selector
                )
                verified = text in (value or '') or len(value or '') > 0
            except Exception:
                verified = True  # assume OK if verify fails

            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("type", selector, f"Typed {len(text)} chars", verified)
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_type",
                "target": selector, "error": None,
                "result": f"Typed {len(text)} chars into '{selector}'"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_type failed on '{selector}' for session {session_id}: {e}")
            session.memory.record_step("type", selector, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_type", "target": selector, "error": str(e)}

    async def browser_submit(self, selector: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit a form or press Enter."""
        session = self._get_session(session_id)
        start = time.perf_counter()
        try:
            page = await self._ensure_page(session_id)
            url_before = page.url
            submitted = False

            if selector:
                try:
                    result = await page.evaluate(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            if (el) {
                                const form = el.closest('form');
                                if (form) { form.submit(); return 'form_submit'; }
                                el.click(); return 'element_click';
                            }
                            return 'not_found';
                        }""",
                        selector
                    )
                    submitted = result in ("form_submit", "element_click")
                except Exception:
                    pass

            if not submitted:
                await page.keyboard.press("Enter")
                submitted = True

            await asyncio.sleep(1.0)
            await self._update_memory_from_page(session_id)
            url_changed = page.url != url_before
            verified = submitted and (url_changed or bool(session.memory.page_title))
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("submit", selector or "active_element",
                                     f"Submitted. URL changed: {url_changed}", verified)
            return {
                "success": submitted, "verified": verified,
                "execution_time": elapsed, "tool": "browser_submit",
                "target": selector or "active_element", "error": None,
                "result": f"Submitted. Now at: {session.memory.page_title}"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_submit failed for session {session_id}: {e}")
            session.memory.record_step("submit", selector or "active_element", str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_submit", "target": selector or "active_element",
                    "error": str(e)}

    # ---------------------------------------------------------------------------
    # Tab management
    # ---------------------------------------------------------------------------

    async def browser_tab_management(self, action: str, target: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Manage tabs: new, close, switch, list."""
        session = self._get_session(session_id)
        start = time.perf_counter()
        try:
            await self._ensure_page(session_id)
            ctx = session._context
            assert ctx is not None, "Browser context not initialized"
            pages = ctx.pages

            if action == "new":
                new_page = await ctx.new_page()
                session._page = new_page
                if target:
                    await new_page.goto(target, wait_until="domcontentloaded", timeout=15000)
                await self._update_memory_from_page(session_id)
                elapsed = f"{time.perf_counter() - start:.2f}s"
                session.memory.record_step("tab_new", target or "blank", "New tab opened", True)
                return {
                    "success": True, "verified": True,
                    "execution_time": elapsed, "tool": "browser_tab_management",
                    "target": target or "blank", "error": None,
                    "result": f"Opened new tab. URL: {target or 'about:blank'}"
                }

            elif action == "close":
                if session._page and not session._page.is_closed():
                    await session._page.close()
                    remaining = [p for p in ctx.pages if not p.is_closed()]
                    session._page = remaining[-1] if remaining else await ctx.new_page()
                await self._update_memory_from_page(session_id)
                elapsed = f"{time.perf_counter() - start:.2f}s"
                session.memory.record_step("tab_close", "current", f"{len(ctx.pages)} tabs remaining", True)
                return {
                    "success": True, "verified": True,
                    "execution_time": elapsed, "tool": "browser_tab_management",
                    "target": "current_tab", "error": None,
                    "result": f"Closed tab. {len(ctx.pages)} tab(s) remaining."
                }

            elif action == "switch":
                switched = False
                if target is not None:
                    if target.isdigit():
                        idx = int(target)
                        if 0 <= idx < len(pages):
                            session._page = pages[idx]
                            await session._page.bring_to_front()
                            switched = True
                    else:
                        try:
                            from rapidfuzz import fuzz, process as rfp
                            titles = [p.url + " " + (await p.title()) for p in pages]
                            best = rfp.extractOne(target, titles, scorer=fuzz.token_set_ratio, score_cutoff=50)
                            if best:
                                idx = titles.index(best[0])
                                session._page = pages[idx]
                                await session._page.bring_to_front()
                                switched = True
                        except ImportError:
                            pass

                if switched:
                    await self._update_memory_from_page(session_id)
                elapsed = f"{time.perf_counter() - start:.2f}s"
                session.memory.record_step("tab_switch", target or "", "Switched" if switched else "Tab not found", switched)
                return {
                    "success": switched, "verified": switched,
                    "execution_time": elapsed, "tool": "browser_tab_management",
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
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": True, "verified": True,
                    "execution_time": elapsed, "tool": "browser_tab_management",
                    "target": "all_tabs", "error": None,
                    "result": tab_info
                }

            else:
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {
                    "success": False, "verified": False,
                    "execution_time": elapsed, "tool": "browser_tab_management",
                    "target": action, "error": f"Unknown action: '{action}'. Use new/close/switch/list."
                }

        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_tab_management failed: {e}")
            session.memory.record_step(f"tab_{action}", target or "", str(e), False)
            return {
                "success": False, "verified": False,
                "execution_time": elapsed, "tool": "browser_tab_management",
                "target": action, "error": str(e)
            }

    # ---------------------------------------------------------------------------
    # Phase C: Goal-Oriented Agent Execution Loop
    # ---------------------------------------------------------------------------

    async def run_browser_task(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        on_step_complete: Optional[Any] = None,  # async callback(step_result)
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a multi-step browser task with Observe-Decide-Execute-Verify per step.
        """
        session = self._get_session(session_id)
        logger.info(f"🤖 [BrowserTask] Goal: '{goal}' | Steps: {len(steps)} | Session: {session.session_id}")
        session.memory.session_state = "interacting"
        session.memory.last_action = "start_task"

        results = []
        completed = 0
        total = len(steps)

        for i, step in enumerate(steps):
            action = step.get("action", "")
            target = step.get("target", "")
            text = step.get("text", "")
            logger.info(f"  Step {i+1}/{total}: {action}({target!r})")

            # --- OBSERVE phase (before action) ---
            observation = await self.observe(session_id)

            # --- EXECUTE phase with RETRY LOOP ---
            step_result: Dict[str, Any] = {}
            max_retries = 3
            
            for attempt in range(1, max_retries + 1):
                try:
                    if action == "open_url":
                        step_result = await self.open_url(target, session_id)
                    elif action == "search":
                        step_result = await self.search(target, session_id)
                    elif action == "click":
                        step_result = await self._smart_click(target, session_id)
                    elif action == "type":
                        step_result = await self.browser_type(target, text, session_id)
                    elif action == "submit":
                        step_result = await self.browser_submit(target or None, session_id)
                    elif action == "observe":
                        step_result = {"success": True, "verified": True, "result": observation}
                    elif action == "screenshot":
                        step_result = await self.screenshot(session_id=session_id)
                    elif action == "wait":
                        secs = float(target) if target else 1.0
                        await asyncio.sleep(min(secs, 10.0))
                        step_result = {"success": True, "verified": True, "result": f"Waited {secs}s"}
                    elif action == "verify_url":
                        await self._update_memory_from_page(session_id)
                        found = target.lower() in session.memory.current_url.lower()
                        step_result = {
                            "success": found, "verified": found,
                            "result": f"URL {'contains' if found else 'does not contain'} '{target}'"
                        }
                    elif action == "verify_text":
                        found = await self._find_text_on_page(target, session_id)
                        step_result = {
                            "success": found, "verified": found,
                            "result": f"Text '{target}' {'found' if found else 'NOT found'} on page"
                        }
                    else:
                        step_result = {"success": False, "verified": False, "error": f"Unknown action: {action}"}
                        break # Don't retry unknown actions
                        
                    # If success, break the retry loop
                    if step_result.get("success"):
                        break
                    else:
                        raise Exception(step_result.get("error", "Action returned success=False"))
                        
                except Exception as e:
                    step_result = {"success": False, "verified": False, "error": str(e)}
                    if attempt < max_retries:
                        backoff = attempt * 1.5
                        logger.warning(f"  ⚠️ Step {i+1} failed (Attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        # Force observation refresh before retry
                        observation = await self.observe(session_id)
                    else:
                        logger.error(f"  ❌ Step {i+1} critically failed after {max_retries} attempts: {e}")

            # --- VERIFY phase ---
            step_result["step"] = i + 1
            step_result["action"] = action
            step_result["target"] = target
            step_result["observation_before"] = {
                "url": observation.get("url"),
                "title": observation.get("title"),
            }
            results.append(step_result)

            if step_result.get("success"):
                completed += 1
                result_str = str(step_result.get("result", ""))
                logger.info(f"  ✅ Step {i+1} passed: {result_str[:100]}")
            else:
                logger.warning(f"  ❌ Step {i+1} failed: {step_result.get('error', 'Unknown error')}")

            # Notify caller
            if on_step_complete:
                try:
                    await on_step_complete(step_result)
                except Exception:
                    pass

            # Stop on critical failure
            if not step_result.get("success") and step.get("stop_on_fail", False):
                logger.warning(f"  🛑 Stopping task at step {i+1} (stop_on_fail=True)")
                break

        # Final memory update
        await self._update_memory_from_page(session_id)
        session.memory.session_state = "completed" if completed == total else "error"

        overall_success = completed > 0 and completed == total
        logger.info(f"🤖 [BrowserTask] Done: {completed}/{total} steps succeeded")
        return {
            "success": overall_success,
            "verified": overall_success,
            "goal": goal,
            "steps_completed": completed,
            "steps_total": total,
            "final_url": session.memory.current_url,
            "final_title": session.memory.page_title,
            "results": results,
        }

    # ---------------------------------------------------------------------------
    # Smart helpers for Phase C
    # ---------------------------------------------------------------------------

    async def _smart_click(self, target: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Click using 7-level LocatorEngine cascade."""
        from core.browser_locator import locator_engine, LocatorNotFoundError
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        url_before = page.url
        start = time.perf_counter()

        try:
            clicked = await locator_engine.click_element(page, target, timeout=5000)
            if not clicked:
                raise Exception(f"LocatorEngine could not click '{target}'")
            await asyncio.sleep(0.5)
            await self._update_memory_from_page(session_id)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("click", target, "Clicked (LocatorEngine)", True)
            return {
                "success": True, "verified": True,
                "execution_time": elapsed, "tool": "browser_click",
                "target": target, "error": None,
                "result": f"Clicked '{target}'. Now: {session.memory.page_title}"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("click", target, str(e), False)
            return {
                "success": False, "verified": False,
                "execution_time": elapsed, "tool": "browser_click",
                "target": target, "error": f"Could not find clickable element: '{target}'. {e}"
            }

    async def _find_text_on_page(self, text: str, session_id: Optional[str] = None) -> bool:
        """Check if specific text is visible on the current page."""
        try:
            page = await self._ensure_page(session_id)
            result = await page.evaluate(
                "(text) => document.body.innerText.toLowerCase().includes(text.toLowerCase())",
                text
            )
            return bool(result)
        except Exception:
            return False


    # ---------------------------------------------------------------------------
    # Phase 8: LLM-Driven Observe-Decide-Act-Verify Agentic Loop
    # ---------------------------------------------------------------------------

    _AGENTIC_SYSTEM_PROMPT = """You are a browser automation agent. Your job is to complete the user's goal by controlling a web browser.

At each iteration you will receive:
- GOAL: The overall objective
- CURRENT STATE: URL, page title, visible buttons, inputs, links, and text on screen
- HISTORY: Previous actions and results

Respond with a JSON object (ONLY JSON, no markdown) describing the NEXT single action to take:

{
  "action": "<action_name>",
  "target": "<CSS selector, URL, or text to interact with>",
  "text": "<text to type, if action=type>",
  "reasoning": "<1-2 sentence explanation>",
  "done": false
}

Available actions:
- open_url: Navigate to a URL. target = full URL.
- click: Click an element. target = CSS selector or visible text.
- type: Type text into a field. target = CSS selector. text = what to type.
- submit: Submit a form or press Enter. target = optional CSS selector.
- search: Type in the main search box and submit. target = search query.
- wait: Wait N seconds. target = number of seconds as string.
- verify_text: Check if text is visible. target = text to look for.
- scroll: Scroll the page down. target = "down" or "up".

If the goal is fully achieved, set "done": true.
If you cannot proceed (error loop, missing auth, bot detection), set "done": true with reasoning explaining why.

IMPORTANT: Output ONLY valid JSON. No backticks, no markdown, no extra text."""

    async def run_agentic_task(
        self,
        goal: str,
        session_id: Optional[str] = None,
        max_iterations: int = 12,
        on_step_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        LLM-driven autonomous Observe→Decide→Act→Verify loop.

        Unlike run_browser_task (caller-defined steps), this method lets the
        Generals-tier LLM (Cerebras 120B via model_router) decide what to do
        at each step based on live DOM state observation.

        Safeguards:
        - Caps at max_iterations (default 12) — prevents infinite loops
        - Detects stuck state (same URL + same page title 2x in a row) → stops
        - All actions route through existing verified browser primitives

        Returns a full trace including each iteration's observation and action.
        """
        from core.model_router import model_router, TaskClass

        session = self._get_session(session_id)
        session.memory.session_state = "interacting"
        logger.info(f"🤖 [AgenticLoop] Goal: '{goal}' | Max iterations: {max_iterations} | Session: {session.session_id}")

        trace: List[Dict[str, Any]] = []
        history_lines: List[str] = []
        completed_iterations = 0
        last_fingerprint = ""

        for iteration in range(1, max_iterations + 1):
            logger.info(f"  [Iter {iteration}/{max_iterations}] Observing page state...")

            # ── OBSERVE ──────────────────────────────────────────────────────
            observation = await self.observe(session_id)
            current_url   = observation.get("url", "about:blank")
            current_title = observation.get("title", "")

            # Collect DOM snapshot for context
            dom_summary_parts = []
            snap = observation.get("snapshot", {})
            buttons = snap.get("buttons", [])[:8]
            inputs  = snap.get("inputs", [])[:6]
            links   = snap.get("links", [])[:8]
            texts   = snap.get("text", [])[:10]

            if buttons:
                dom_summary_parts.append("Buttons: " + " | ".join(
                    f"[{b.get('text', '?')}]({b.get('selector', '')})" for b in buttons
                ))
            if inputs:
                dom_summary_parts.append("Inputs: " + " | ".join(
                    f"[{i.get('type', 'text')} name={i.get('name', '')} id={i.get('id', '')}]" for i in inputs
                ))
            if links:
                dom_summary_parts.append("Links: " + " | ".join(
                    f"[{lk.get('text', '?')}]({lk.get('href', '')})" for lk in links if lk.get('text')
                )[:400])
            if texts:
                dom_summary_parts.append("Text: " + " / ".join(str(t)[:80] for t in texts[:5]))

            dom_summary = "\n".join(dom_summary_parts) if dom_summary_parts else "(no visible interactive elements)"

            current_state = (
                f"URL: {current_url}\n"
                f"Title: {current_title}\n"
                f"{dom_summary}"
            )

            # Stuck-state detection: same URL + same title 3x in a row AND past iter 3
            fingerprint = f"{current_url}::{current_title}"
            if fingerprint == last_fingerprint and iteration > 3:
                stuck_count = getattr(self, '_stuck_count', 0) + 1
                self._stuck_count = stuck_count
                if stuck_count >= 3:
                    logger.warning(f"  [AgenticLoop] Stuck state detected at '{current_url}' ({stuck_count}x). Stopping.")
                    trace.append({"iteration": iteration, "observation": current_state, "action": None,
                                   "result": "STUCK_STATE", "success": False})
                    self._stuck_count = 0
                    break
            else:
                self._stuck_count = 0
            last_fingerprint = fingerprint

            # ── DECIDE ───────────────────────────────────────────────────────
            history_context = "\n".join(history_lines[-6:]) if history_lines else "(no prior actions)"
            decide_messages = [{
                "role": "user",
                "content": (
                    f"GOAL: {goal}\n\n"
                    f"CURRENT STATE:\n{current_state}\n\n"
                    f"HISTORY (last 6 actions):\n{history_context}\n\n"
                    f"What is the NEXT single action to take? Reply with JSON only."
                )
            }]

            raw_decision: str = ""
            try:
                raw_decision = await model_router.route_task(
                    task_class=TaskClass.BROWSER,
                    system_prompt=self._AGENTIC_SYSTEM_PROMPT,
                    messages=decide_messages,
                )
                # Extract JSON block using regex to handle extra conversational text
                import re
                clean = raw_decision.strip()
                json_match = re.search(r"\{.*\}", clean, re.DOTALL)
                if json_match:
                    clean = json_match.group(0)
                decision = json.loads(clean)
            except json.JSONDecodeError:
                logger.warning(f"  [AgenticLoop] LLM returned non-JSON: {raw_decision[:200]}")
                trace.append({"iteration": iteration, "observation": current_state,
                               "action": "PARSE_ERROR", "result": raw_decision, "success": False})
                break
            except Exception as e:
                logger.error(f"  [AgenticLoop] LLM decision failed: {e}")
                trace.append({"iteration": iteration, "observation": current_state,
                               "action": "LLM_ERROR", "result": str(e), "success": False})
                break

            action   = decision.get("action", "")
            target   = decision.get("target", "")
            text     = decision.get("text", "")
            is_done  = bool(decision.get("done", False))
            reasoning = decision.get("reasoning", "")

            # Validate LLM action against allowlist — never hallucinate execution
            _VALID_ACTIONS = {
                "open_url", "click", "type", "submit", "search", "wait",
                "verify_text", "verify_url", "scroll", "extract", "back",
                "forward", "refresh", "select", "done", "fail"
            }
            if action and action not in _VALID_ACTIONS:
                logger.warning(f"  [AgenticLoop] LLM returned invalid action '{action}' — REJECTED")
                history_lines.append(f"[{iteration}] INVALID_ACTION({action!r}) → ❌ rejected")
                continue

            logger.info(f"  [Iter {iteration}] Decision: {action}({target!r}) — {reasoning[:80]}")

            if is_done:
                logger.info(f"  [AgenticLoop] LLM signalled goal complete at iteration {iteration}.")
                trace.append({"iteration": iteration, "observation": current_state,
                               "action": "DONE", "result": reasoning, "success": True})
                completed_iterations = iteration
                break

            # ── ACT ───────────────────────────────────────────────────────────
            step_result: Dict[str, Any] = {}
            try:
                if action == "open_url":
                    step_result = await self.open_url(target, session_id)
                elif action == "click":
                    step_result = await self._smart_click(target, session_id)
                elif action == "type":
                    step_result = await self.browser_type(target, text, session_id)
                elif action == "submit":
                    step_result = await self.browser_submit(target or None, session_id)
                elif action == "search":
                    step_result = await self.search(target, session_id)
                elif action == "wait":
                    secs = min(float(target) if target else 2.0, 10.0)
                    await asyncio.sleep(secs)
                    step_result = {"success": True, "verified": True, "result": f"Waited {secs}s"}
                elif action == "verify_text":
                    found = await self._find_text_on_page(target, session_id)
                    step_result = {"success": found, "verified": found,
                                   "result": f"Text '{target}' {'found' if found else 'NOT found'}"}
                elif action == "scroll":
                    page = await self._ensure_page(session_id)
                    delta = 600 if (target or "down").lower() == "down" else -600
                    await page.evaluate(f"window.scrollBy(0, {delta})")
                    await asyncio.sleep(0.5)
                    step_result = {"success": True, "verified": True, "result": f"Scrolled {target or 'down'}"}
                else:
                    step_result = {"success": False, "verified": False,
                                   "error": f"Unknown action returned by LLM: '{action}'"}
            except Exception as e:
                step_result = {"success": False, "verified": False, "error": str(e)}
                logger.error(f"  [AgenticLoop] Action '{action}' raised: {e}")

            # ── VERIFY ───────────────────────────────────────────────────────
            success = step_result.get("success", False)
            result_str = str(step_result.get("result", step_result.get("error", "")))[:200]

            history_lines.append(
                f"[{iteration}] {action}({target!r}) → {'✅' if success else '❌'} {result_str}"
            )
            trace.append({
                "iteration": iteration,
                "observation": {"url": current_url, "title": current_title},
                "action": action,
                "target": target,
                "text": text,
                "reasoning": reasoning,
                "result": step_result,
                "success": success,
            })

            # Notify caller (e.g. voice_session can stream trace to frontend)
            if on_step_complete:
                try:
                    await on_step_complete({
                        "iteration": iteration,
                        "action": action,
                        "target": target,
                        "success": success,
                        "result": result_str,
                    })
                except Exception:
                    pass

            completed_iterations = iteration

        # Final page state
        await self._update_memory_from_page(session_id)
        session.memory.session_state = "completed"
        overall_success = any(t.get("action") == "DONE" for t in trace) or (
            completed_iterations > 0 and trace[-1].get("success", False)
        )

        logger.info(
            f"🤖 [AgenticLoop] Finished. Iterations: {completed_iterations}/{max_iterations} | "
            f"Overall success: {overall_success}"
        )
        return {
            "success": overall_success,
            "verified": overall_success,
            "goal": goal,
            "iterations_used": completed_iterations,
            "max_iterations": max_iterations,
            "final_url": session.memory.current_url,
            "final_title": session.memory.page_title,
            "trace": trace,
        }

    async def close(self, session_id: Optional[str] = None) -> None:
        """Clean up Playwright resources for a specific session."""
        s_id = session_id or "default"
        if s_id in self._sessions:
            session = self._sessions[s_id]
            await session.close()
            del self._sessions[s_id]
            logger.info(f"🧹 Cleaned up browser session: {s_id}")


browser_agent = BrowserAgent()
