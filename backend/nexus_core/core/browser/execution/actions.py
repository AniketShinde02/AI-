"""
browser/execution/actions.py
==============================
Nexus Browser Domain — Core Action Primitives

Single Responsibility: Execute discrete, deterministic browser actions
(open_url, click, type, submit, scroll, upload, download, tab management).
Each method returns an ActionResult-compatible dict.

Dependency Rule: imports from session/, resiliency/, verification/, models/ only.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from core.browser.models import BrowserStateEnum
from core.browser.resiliency import locator_engine, LocatorNotFoundError

logger = logging.getLogger("nexus.browser.execution")

_SEARCH_SHORTCUTS: Dict[str, str] = {
    "youtube.com":   "https://www.youtube.com/results?search_query={q}",
    "github.com":    "https://github.com/search?q={q}",
    "amazon.com":    "https://www.amazon.com/s?k={q}",
    "wikipedia.org": "https://en.wikipedia.org/wiki/Special:Search?search={q}",
    "reddit.com":    "https://www.reddit.com/search/?q={q}",
}


class ActionEngine:
    """Stateless action executor. Receives a page and session context per call."""

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def open_url(self, page: Any, session: Any, url: str) -> Dict[str, Any]:
        start = time.perf_counter()
        await session.state_machine.transition_to(BrowserStateEnum.NAVIGATING, {"url": url})
        await asyncio.sleep(random.uniform(1.0, 2.5))  # Anti-fingerprint jitter

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            if response and response.status == 429:
                logger.warning(f"⚠️ 429 on {url} — backing off")
                await session.state_machine.transition_to(BrowserStateEnum.RECOVERING)
                await asyncio.sleep(random.uniform(5.0, 10.0))
                await session.state_machine.transition_to(BrowserStateEnum.NAVIGATING)
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            await session.state_machine.transition_to(BrowserStateEnum.VERIFYING)
            from core.browser.verification import nav_verifier
            verified = await nav_verifier.verify(
                page, response=response,
                expected_url_fragment=url.split("//")[-1].split("/")[0],
                current_url=page.url,
                page_title=await page.title(),
            )
            elapsed = f"{time.perf_counter() - start:.2f}s"

            if verified:
                await session.state_machine.transition_to(BrowserStateEnum.COMPLETED)
                title = await page.title()
                session.memory.record_step("open_url", url, f"Navigated to {title}", True)
                return {"success": True, "verified": True, "execution_time": elapsed,
                        "tool": "browser_open_url", "target": url,
                        "result": f"Opened '{title}' ({page.url})"}
            else:
                await session.state_machine.transition_to(BrowserStateEnum.FAILED)
                session.memory.record_step("open_url", url, "Verification failed", False)
                return {"success": False, "verified": False, "execution_time": elapsed,
                        "tool": "browser_open_url", "target": url,
                        "error": "Navigation verification failed"}
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            await session.state_machine.transition_to(BrowserStateEnum.FAILED)
            session.memory.record_step("open_url", url, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_open_url", "target": url, "error": str(e)}

    async def search(self, page: Any, session: Any, query: str) -> Dict[str, Any]:
        encoded = urllib.parse.quote(query)
        current_url = session.memory.current_url or "about:blank"
        for domain, pattern in _SEARCH_SHORTCUTS.items():
            if domain in current_url:
                url = pattern.format(q=encoded)
                logger.info(f"[Search] Context-aware → {url}")
                return await self.open_url(page, session, url)
        url = f"https://duckduckgo.com/?q={encoded}"
        logger.info(f"[Search] DuckDuckGo → {url}")
        return await self.open_url(page, session, url)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    async def click(self, page: Any, session: Any, target: str) -> Dict[str, Any]:
        start = time.perf_counter()
        url_before = page.url
        try:
            clicked = await locator_engine.click_element(page, target)
            if not clicked:
                raise LocatorNotFoundError(f"Cannot find: {target!r}")
            await asyncio.sleep(0.5)
            title = await page.title()
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("click", target, "Clicked", True)
            return {"success": True, "verified": True, "execution_time": elapsed,
                    "tool": "browser_click", "target": target,
                    "result": f"Clicked '{target}'. Now: {title}"}
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("click", target, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_click", "target": target, "error": str(e)}

    async def type_text(self, page: Any, session: Any, selector: str, text: str) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            filled = await locator_engine.fill_element(page, selector, text)
            if not filled:
                raise LocatorNotFoundError(f"Cannot fill: {selector!r}")
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("type", selector, f"Typed {len(text)} chars", True)
            return {"success": True, "verified": True, "execution_time": elapsed,
                    "tool": "browser_type", "target": selector,
                    "result": f"Typed {len(text)} chars into '{selector}'"}
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("type", selector, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_type", "target": selector, "error": str(e)}

    async def submit(self, page: Any, session: Any, selector: Optional[str] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        url_before = page.url
        submitted = False
        try:
            if selector:
                try:
                    result = await page.evaluate("""
                    (sel) => {
                        const el = document.querySelector(sel);
                        if (el) {
                            const form = el.closest('form');
                            if (form) { form.submit(); return 'form_submit'; }
                            el.click(); return 'element_click';
                        }
                        return 'not_found';
                    }""", selector)
                    submitted = result in ("form_submit", "element_click")
                except Exception:
                    pass
            if not submitted:
                await page.keyboard.press("Enter")
                submitted = True
            await asyncio.sleep(1.0)
            title = await page.title()
            url_changed = page.url != url_before
            verified = submitted and (url_changed or bool(title))
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("submit", selector or "active_element", f"Submitted. URL changed: {url_changed}", verified)
            return {"success": submitted, "verified": verified, "execution_time": elapsed,
                    "tool": "browser_submit", "target": selector or "active_element",
                    "result": f"Submitted. Now: {title}"}
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("submit", selector or "active_element", str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_submit", "target": selector or "active_element", "error": str(e)}

    async def scroll(self, page: Any, session: Any, direction: str = "down") -> Dict[str, Any]:
        delta = 600 if direction.lower() != "up" else -600
        try:
            await page.evaluate(f"window.scrollBy(0, {delta})")
            await asyncio.sleep(0.5)
            return {"success": True, "verified": True, "tool": "browser_scroll",
                    "target": direction, "result": f"Scrolled {direction}"}
        except Exception as e:
            return {"success": False, "verified": False, "tool": "browser_scroll",
                    "target": direction, "error": str(e)}

    async def infinite_scroll(self, page: Any, session: Any, max_iterations: int = 5) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            await session.state_machine.transition_to(BrowserStateEnum.EXECUTING, {"action": "infinite_scroll"})
            for _ in range(max_iterations):
                last_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                try:
                    await page.wait_for_load_state("networkidle", timeout=2000)
                except Exception:
                    await asyncio.sleep(1.0)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
            await session.state_machine.transition_to(BrowserStateEnum.COMPLETED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("scroll", "infinite", "Scrolled to bottom", True)
            return {"success": True, "verified": True, "execution_time": elapsed,
                    "tool": "browser_infinite_scroll", "target": "bottom", "result": "Scrolled"}
        except Exception as e:
            await session.state_machine.transition_to(BrowserStateEnum.FAILED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_infinite_scroll", "target": "bottom", "error": str(e)}

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    async def download(self, page: Any, session: Any, target_selector: str, dest: str) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            await session.state_machine.transition_to(BrowserStateEnum.EXECUTING, {"action": "download"})
            locator = await locator_engine.locate(page, target_selector)
            async with page.expect_download() as dl_info:
                await locator.click(force=True, timeout=5000)
            download = await dl_info.value
            await download.save_as(dest)
            session.memory.downloads.append(dest)
            await session.state_machine.transition_to(BrowserStateEnum.COMPLETED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("download", target_selector, f"Downloaded to {dest}", True)
            return {"success": True, "verified": True, "execution_time": elapsed,
                    "tool": "browser_download", "target": dest, "result": f"Downloaded to '{dest}'"}
        except Exception as e:
            await session.state_machine.transition_to(BrowserStateEnum.FAILED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_download", "target": dest, "error": str(e)}

    async def upload(self, page: Any, session: Any, selector: str, file_path: str) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File '{file_path}' not found")
            await session.state_machine.transition_to(BrowserStateEnum.EXECUTING, {"action": "upload"})
            locator = await locator_engine.locate(page, selector)
            async with page.expect_file_chooser() as fc_info:
                await locator.click(force=True, timeout=5000)
            fc = await fc_info.value
            await fc.set_files(file_path)
            session.memory.uploads.append(file_path)
            await session.state_machine.transition_to(BrowserStateEnum.COMPLETED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            session.memory.record_step("upload", selector, f"Uploaded {file_path}", True)
            return {"success": True, "verified": True, "execution_time": elapsed,
                    "tool": "browser_upload", "target": selector,
                    "result": f"Uploaded '{file_path}' to '{selector}'"}
        except Exception as e:
            await session.state_machine.transition_to(BrowserStateEnum.FAILED)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_upload", "target": selector, "error": str(e)}

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    async def manage_tabs(self, page: Any, session: Any, action: str, target: Optional[str] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        ctx = session._context
        try:
            assert ctx is not None, "Browser context not initialized"
            pages: List[Any] = ctx.pages

            if action == "new":
                new_page = await ctx.new_page()
                session._page = new_page
                if target:
                    await new_page.goto(target, wait_until="domcontentloaded", timeout=15000)
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {"success": True, "verified": True, "execution_time": elapsed,
                        "tool": "browser_tab_management", "target": target or "blank",
                        "result": f"Opened new tab. URL: {target or 'about:blank'}"}

            elif action == "close":
                if session._page and not session._page.is_closed():
                    await session._page.close()
                remaining = [p for p in ctx.pages if not p.is_closed()]
                session._page = remaining[-1] if remaining else await ctx.new_page()
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {"success": True, "verified": True, "execution_time": elapsed,
                        "tool": "browser_tab_management", "target": "current_tab",
                        "result": f"Closed tab. {len(ctx.pages)} remaining."}

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
                                session._page = pages[titles.index(best[0])]
                                await session._page.bring_to_front()
                                switched = True
                        except ImportError:
                            pass
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {"success": switched, "verified": switched, "execution_time": elapsed,
                        "tool": "browser_tab_management", "target": target,
                        "error": None if switched else "Tab not found"}

            elif action == "list":
                tab_info = []
                for i, p in enumerate(pages):
                    try:
                        t = await p.title()
                    except Exception:
                        t = "(loading)"
                    tab_info.append(f"[{i}] {t} — {p.url}")
                elapsed = f"{time.perf_counter() - start:.2f}s"
                return {"success": True, "verified": True, "execution_time": elapsed,
                        "tool": "browser_tab_management", "target": "all_tabs", "result": tab_info}

            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_tab_management", "target": action,
                    "error": f"Unknown tab action: '{action}'. Use new/close/switch/list."}

        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_tab_management", "target": action, "error": str(e)}


action_engine = ActionEngine()
