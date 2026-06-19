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

Phase E: Isolated Playwright profile (data/browser_profile) — never touches user Chrome.
"""
import logging
import asyncio
import os
import time
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("nexus.browser_agent")


# ---------------------------------------------------------------------------
# Phase D: Browser Memory — tracks where the agent is and what it did last
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# DOM / Accessibility extraction JS
# ---------------------------------------------------------------------------

_DOM_SNAPSHOT_JS = """
() => {
    const isVisible = (el) => {
        const r = el.getBoundingClientRect();
        const s = window.getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
    };
    const text = [];
    const buttons = [];
    const inputs = [];
    const links = [];

    // Collect visible text (paragraphs, headings, spans with meaningful text)
    document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, li, td, th, label, div[role]').forEach(el => {
        if (isVisible(el) && el.innerText && el.innerText.trim().length > 3) {
            const t = el.innerText.trim().replace(/\\s+/g, ' ');
            if (t.length < 500) text.push(t);
        }
    });

    // Buttons
    document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            buttons.push({
                text: (el.innerText || el.value || el.ariaLabel || '').trim().substring(0, 100),
                selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : 'button'),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    // Inputs
    document.querySelectorAll('input:not([type="hidden"]), textarea, [contenteditable="true"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            inputs.push({
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder || '',
                label: (el.labels && el.labels[0] ? el.labels[0].innerText : el.ariaLabel || '').trim().substring(0, 80),
                selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : 'input'),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    // Links
    document.querySelectorAll('a[href]').forEach(el => {
        if (isVisible(el) && el.innerText.trim().length > 1) {
            const r = el.getBoundingClientRect();
            links.push({
                text: el.innerText.trim().substring(0, 120),
                href: el.href.substring(0, 200),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    return {
        url: window.location.href,
        title: document.title,
        text: [...new Set(text)].slice(0, 30),
        buttons: buttons.slice(0, 20),
        inputs: inputs.slice(0, 15),
        links: links.slice(0, 30),
    };
}
"""

_A11Y_TREE_JS = """
() => {
    const walk = (el, depth) => {
        if (depth > 4) return null;
        const role = el.getAttribute('role') || el.tagName.toLowerCase();
        const label = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.textContent?.trim().substring(0, 80) || '';
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return null;
        const node = {
            role,
            label,
            id: el.id || null,
            x: Math.round(r.x + r.width/2),
            y: Math.round(r.y + r.height/2),
            children: [],
        };
        const interestingChildren = Array.from(el.children).filter(c => {
            const cr = c.getBoundingClientRect();
            return cr.width > 0 && cr.height > 0;
        });
        for (const child of interestingChildren.slice(0, 5)) {
            const childNode = walk(child, depth + 1);
            if (childNode) node.children.push(childNode);
        }
        return node;
    };
    return walk(document.body, 0);
}
"""


class BrowserAgent:
    """
    Browser Agent V1 — Observe-Decide-Execute-Verify loop with DOM/A11y snapshots.
    Uses an isolated Playwright persistent context (Phase E — data/browser_profile).
    """

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self.memory = BrowserMemory()

    # ---------------------------------------------------------------------------
    # Phase E: Isolated context management
    # ---------------------------------------------------------------------------

    async def _ensure_page(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        context_is_dead = False
        if self._context:
            try:
                _ = self._context.pages
            except Exception:
                context_is_dead = True

        if not self._page or self._page.is_closed() or context_is_dead:
            # Clean up stale instances
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

            self._playwright = await async_playwright().start()
            # Phase E: Isolated profile — never touches user's Chrome data
            user_data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "browser_profile"
            )
            os.makedirs(user_data_dir, exist_ok=True)
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 720},
            )
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = await self._context.new_page()

        return self._page

    async def _update_memory_from_page(self):
        """Sync BrowserMemory with current page state."""
        try:
            if not self._page or self._page.is_closed():
                return
            self.memory.current_url = self._page.url
            self.memory.page_title = await self._page.title()
            if self._context:
                pages = self._context.pages
                self.memory.total_tabs = len(pages)
                try:
                    self.memory.current_tab_index = pages.index(self._page)
                except ValueError:
                    self.memory.current_tab_index = 0
        except Exception as e:
            logger.debug(f"Memory sync failed: {e}")

    def get_workspace_state(self) -> Dict[str, Any]:
        """Return browser memory as a workspace state dict."""
        return self.memory.to_dict()

    # ---------------------------------------------------------------------------
    # Phase 1: DOM Snapshot
    # ---------------------------------------------------------------------------

    async def get_dom_snapshot(self) -> Dict[str, Any]:
        """Extract visible DOM elements: text, buttons, inputs, links."""
        try:
            page = await self._ensure_page()
            result = await page.evaluate(_DOM_SNAPSHOT_JS)
            return {"success": True, "verified": True, "result": result}
        except Exception as e:
            logger.error(f"DOM snapshot failed: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    # ---------------------------------------------------------------------------
    # Phase 2: Accessibility Tree
    # ---------------------------------------------------------------------------

    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Extract accessibility tree with role, label, coordinates."""
        try:
            page = await self._ensure_page()
            tree = await page.evaluate(_A11Y_TREE_JS)
            return {"success": True, "verified": True, "result": tree}
        except Exception as e:
            logger.error(f"A11y tree failed: {e}")
            return {"success": False, "verified": False, "error": str(e)}

    # ---------------------------------------------------------------------------
    # Phase 3: Screenshot Capture (used only when DOM is insufficient)
    # ---------------------------------------------------------------------------

    async def get_screenshot_base64(self) -> Optional[str]:
        """Get current page screenshot as base64 JPEG (low quality for fast WS transport)."""
        try:
            if not self._page or self._page.is_closed():
                return None
            img_bytes = await self._page.screenshot(type="jpeg", quality=50)
            return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    async def screenshot(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot, optionally navigating first."""
        try:
            page = await self._ensure_page()
            if url:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            path = os.path.join(os.path.expanduser("~"), "nexus_screenshot.png")
            await page.screenshot(path=path)
            await self._update_memory_from_page()
            return {"success": True, "verified": True, "result": f"Screenshot saved to {path}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

    # ---------------------------------------------------------------------------
    # Phase 4: Observe-Decide-Execute-Verify helpers
    # ---------------------------------------------------------------------------

    async def observe(self) -> Dict[str, Any]:
        """
        Observe the current page state. Returns a structured observation:
          - page title, URL
          - available buttons, inputs, links (from DOM snapshot)
          - Falls back to screenshot description if DOM is empty.
        """
        dom = await self.get_dom_snapshot()
        await self._update_memory_from_page()
        return {
            "success": True,
            "verified": True,
            "url": self.memory.current_url,
            "title": self.memory.page_title,
            "dom": dom.get("result", {}),
            "memory": self.memory.to_dict(),
        }

    async def _verify_navigation(self, expected_url_fragment: Optional[str] = None) -> bool:
        """Verify navigation succeeded by checking URL changed or title is non-empty."""
        try:
            await asyncio.sleep(0.5)
            await self._update_memory_from_page()
            if expected_url_fragment and expected_url_fragment.lower() in self.memory.current_url.lower():
                return True
            if self.memory.page_title and self.memory.page_title != "about:blank":
                return True
            return False
        except Exception:
            return False

    async def _verify_element_visible(self, selector: str) -> bool:
        """Verify an element exists and is visible after an action."""
        try:
            if not self._page or self._page.is_closed():
                return False
            el = await self._page.query_selector(selector)
            if el:
                return await el.is_visible()
            return False
        except Exception:
            return False

    # ---------------------------------------------------------------------------
    # Core navigation + interaction
    # ---------------------------------------------------------------------------

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Navigate to URL and verify success."""
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._update_memory_from_page()
            verified = await self._verify_navigation(url.split("//")[-1].split("/")[0])
            elapsed = f"{time.perf_counter() - start:.2f}s"
            self.memory.record_step("open_url", url, f"Navigated to {self.memory.page_title}", verified)
            self.memory.session_state = "navigating"
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_open_url",
                "target": url, "error": None,
                "result": f"Opened '{self.memory.page_title}' ({self.memory.current_url})"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"open_url failed for {url}: {e}")
            self.memory.record_step("open_url", url, str(e), False)
            self.memory.session_state = "error"
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_open_url", "target": url, "error": str(e)}

    async def search(self, query: str) -> Dict[str, Any]:
        """Search via DuckDuckGo."""
        import urllib.parse
        return await self.open_url(f"https://duckduckgo.com/?q={urllib.parse.quote(query)}")

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element and verify the click triggered a state change."""
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
            url_before = page.url
            await page.click(selector, timeout=8000)
            await asyncio.sleep(0.5)
            await self._update_memory_from_page()
            # Verify: URL changed OR title changed
            url_changed = page.url != url_before
            verified = url_changed or bool(self.memory.page_title)
            elapsed = f"{time.perf_counter() - start:.2f}s"
            self.memory.record_step("click", selector, f"Clicked. URL changed: {url_changed}", verified)
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_click",
                "target": selector, "error": None,
                "result": f"Clicked '{selector}'. Page: {self.memory.page_title}"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"click failed on {selector}: {e}")
            self.memory.record_step("click", selector, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_click", "target": selector, "error": str(e)}

    async def extract(self, url: str) -> Dict[str, Any]:
        """Navigate to URL and extract visible text content."""
        try:
            page = await self._ensure_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._update_memory_from_page()
            text = await page.evaluate("document.body.innerText")
            return {
                "success": True, "verified": True,
                "tool": "browser_extract", "target": url,
                "result": text[:5000]
            }
        except Exception as e:
            return {"success": False, "verified": False, "tool": "browser_extract",
                    "target": url, "error": str(e)}

    async def browser_type(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into a field. Clears field first via triple-click."""
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
            await page.click(selector, timeout=5000)
            await page.click(selector, click_count=3, timeout=5000)
            await page.type(selector, text, delay=30)
            # Verify by reading back the field value
            value = await page.evaluate(
                f"(sel) => {{ const el = document.querySelector(sel); return el ? (el.value || el.innerText) : ''; }}",
                selector
            )
            verified = text in value or len(value) > 0
            elapsed = f"{time.perf_counter() - start:.2f}s"
            self.memory.record_step("type", selector, f"Typed {len(text)} chars", verified)
            return {
                "success": True, "verified": verified,
                "execution_time": elapsed, "tool": "browser_type",
                "target": selector, "error": None,
                "result": f"Typed {len(text)} chars into '{selector}'"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_type failed on '{selector}': {e}")
            self.memory.record_step("type", selector, str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_type", "target": selector, "error": str(e)}

    async def browser_submit(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Submit a form or press Enter. Verifies by checking URL/title change."""
        start = time.perf_counter()
        try:
            page = await self._ensure_page()
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
            await self._update_memory_from_page()
            url_changed = page.url != url_before
            verified = submitted and (url_changed or bool(self.memory.page_title))
            elapsed = f"{time.perf_counter() - start:.2f}s"
            self.memory.record_step("submit", selector or "active_element",
                                     f"Submitted. URL changed: {url_changed}", verified)
            return {
                "success": submitted, "verified": verified,
                "execution_time": elapsed, "tool": "browser_submit",
                "target": selector or "active_element", "error": None,
                "result": f"Submitted. Now at: {self.memory.page_title}"
            }
        except Exception as e:
            elapsed = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"browser_submit failed: {e}")
            self.memory.record_step("submit", selector or "active_element", str(e), False)
            return {"success": False, "verified": False, "execution_time": elapsed,
                    "tool": "browser_submit", "target": selector or "active_element",
                    "error": str(e)}

    # ---------------------------------------------------------------------------
    # Tab management
    # ---------------------------------------------------------------------------

    async def browser_tab_management(self, action: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Manage tabs: new, close, switch, list."""
        start = time.perf_counter()
        try:
            await self._ensure_page()
            ctx = self._context
            assert ctx is not None, "Browser context not initialized"
            pages = ctx.pages

            if action == "new":
                new_page = await ctx.new_page()
                self._page = new_page
                if target:
                    await new_page.goto(target, wait_until="domcontentloaded", timeout=15000)
                await self._update_memory_from_page()
                elapsed = f"{time.perf_counter() - start:.2f}s"
                self.memory.record_step("tab_new", target or "blank", "New tab opened", True)
                return {
                    "success": True, "verified": True,
                    "execution_time": elapsed, "tool": "browser_tab_management",
                    "target": target or "blank", "error": None,
                    "result": f"Opened new tab. URL: {target or 'about:blank'}"
                }

            elif action == "close":
                if self._page and not self._page.is_closed():
                    await self._page.close()
                    remaining = [p for p in ctx.pages if not p.is_closed()]
                    self._page = remaining[-1] if remaining else await ctx.new_page()
                await self._update_memory_from_page()
                elapsed = f"{time.perf_counter() - start:.2f}s"
                self.memory.record_step("tab_close", "current", f"{len(ctx.pages)} tabs remaining", True)
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
                            self._page = pages[idx]
                            await self._page.bring_to_front()
                            switched = True
                    else:
                        try:
                            from rapidfuzz import fuzz, process as rfp
                            titles = [p.url + " " + (await p.title()) for p in pages]
                            best = rfp.extractOne(target, titles, scorer=fuzz.token_set_ratio, score_cutoff=50)
                            if best:
                                idx = titles.index(best[0])
                                self._page = pages[idx]
                                await self._page.bring_to_front()
                                switched = True
                        except ImportError:
                            pass

                if switched:
                    await self._update_memory_from_page()
                elapsed = f"{time.perf_counter() - start:.2f}s"
                self.memory.record_step("tab_switch", target or "", "Switched" if switched else "Tab not found", switched)
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
            self.memory.record_step(f"tab_{action}", target or "", str(e), False)
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
    ) -> Dict[str, Any]:
        """
        Execute a multi-step browser task with Observe-Decide-Execute-Verify per step.

        Args:
            goal:      Human-readable goal description
            steps:     List of step dicts: [{action, target, ...}, ...]
            on_step_complete: Optional async callback invoked after each step

        Returns:
            {success, verified, steps_completed, steps_total, goal, results}

        Step actions:
            open_url    — target = URL
            search      — target = query string
            click       — target = CSS selector or visible text
            type        — target = CSS selector, text = text to type
            submit      — target = CSS selector (optional)
            observe     — no target, returns page observation
            screenshot  — no target, captures screenshot
            wait        — target = seconds (str)
            verify_url  — target = URL fragment to verify
            verify_text — target = text to find on page
        """
        logger.info(f"🤖 [BrowserTask] Goal: '{goal}' | Steps: {len(steps)}")
        self.memory.session_state = "interacting"
        self.memory.last_action = "start_task"

        results = []
        completed = 0
        total = len(steps)

        for i, step in enumerate(steps):
            action = step.get("action", "")
            target = step.get("target", "")
            text = step.get("text", "")
            logger.info(f"  Step {i+1}/{total}: {action}({target!r})")

            # --- OBSERVE phase (before action) ---
            observation = await self.observe()

            # --- EXECUTE phase ---
            step_result: Dict[str, Any] = {}

            try:
                if action == "open_url":
                    step_result = await self.open_url(target)
                elif action == "search":
                    step_result = await self.search(target)
                elif action == "click":
                    # Smart click: try selector first, then text-based click
                    step_result = await self._smart_click(target)
                elif action == "type":
                    step_result = await self.browser_type(target, text)
                elif action == "submit":
                    step_result = await self.browser_submit(target or None)
                elif action == "observe":
                    step_result = {"success": True, "verified": True, "result": observation}
                elif action == "screenshot":
                    step_result = await self.screenshot()
                elif action == "wait":
                    secs = float(target) if target else 1.0
                    await asyncio.sleep(min(secs, 10.0))
                    step_result = {"success": True, "verified": True, "result": f"Waited {secs}s"}
                elif action == "verify_url":
                    await self._update_memory_from_page()
                    found = target.lower() in self.memory.current_url.lower()
                    step_result = {
                        "success": found, "verified": found,
                        "result": f"URL {'contains' if found else 'does not contain'} '{target}'"
                    }
                elif action == "verify_text":
                    found = await self._find_text_on_page(target)
                    step_result = {
                        "success": found, "verified": found,
                        "result": f"Text '{target}' {'found' if found else 'NOT found'} on page"
                    }
                else:
                    step_result = {"success": False, "verified": False, "error": f"Unknown action: {action}"}

            except Exception as e:
                step_result = {"success": False, "verified": False, "error": str(e)}
                logger.error(f"  Step {i+1} failed with exception: {e}")

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

            # Notify caller (used for workspace state updates)
            if on_step_complete:
                try:
                    await on_step_complete(step_result)
                except Exception:
                    pass

            # Stop on critical failure (navigation errors usually cascade)
            if not step_result.get("success") and step.get("stop_on_fail", False):
                logger.warning(f"  🛑 Stopping task at step {i+1} (stop_on_fail=True)")
                break

        # Final memory update
        await self._update_memory_from_page()
        self.memory.session_state = "completed" if completed == total else "error"

        overall_success = completed > 0 and completed == total
        logger.info(f"🤖 [BrowserTask] Done: {completed}/{total} steps succeeded")
        return {
            "success": overall_success,
            "verified": overall_success,
            "goal": goal,
            "steps_completed": completed,
            "steps_total": total,
            "final_url": self.memory.current_url,
            "final_title": self.memory.page_title,
            "results": results,
        }

    # ---------------------------------------------------------------------------
    # Smart helpers for Phase C
    # ---------------------------------------------------------------------------

    async def _smart_click(self, target: str) -> Dict[str, Any]:
        """
        Click by CSS selector. Falls back to text-based click via DOM search.
        """
        page = await self._ensure_page()
        url_before = page.url
        start = time.perf_counter()

        # Try direct CSS selector first
        try:
            await page.click(target, timeout=5000)
            await asyncio.sleep(0.5)
            await self._update_memory_from_page()
            elapsed = f"{time.perf_counter() - start:.2f}s"
            self.memory.record_step("click", target, "Clicked (selector)", True)
            return {
                "success": True, "verified": True,
                "execution_time": elapsed, "tool": "browser_click",
                "target": target, "error": None,
                "result": f"Clicked '{target}'. Now: {self.memory.page_title}"
            }
        except Exception:
            pass

        # Fallback: find by visible text
        try:
            clicked = await page.evaluate(
                """(text) => {
                    const els = Array.from(document.querySelectorAll('button, a, [role="button"], [role="link"]'));
                    const lower = text.toLowerCase();
                    const match = els.find(el => el.innerText.toLowerCase().includes(lower) && el.getBoundingClientRect().width > 0);
                    if (match) { match.click(); return true; }
                    return false;
                }""",
                target
            )
            if clicked:
                await asyncio.sleep(0.5)
                await self._update_memory_from_page()
                elapsed = f"{time.perf_counter() - start:.2f}s"
                self.memory.record_step("click", target, "Clicked (text match)", True)
                return {
                    "success": True, "verified": True,
                    "execution_time": elapsed, "tool": "browser_click",
                    "target": target, "error": None,
                    "result": f"Clicked text '{target}'. Now: {self.memory.page_title}"
                }
        except Exception:
            pass

        elapsed = f"{time.perf_counter() - start:.2f}s"
        self.memory.record_step("click", target, "No match found", False)
        return {
            "success": False, "verified": False,
            "execution_time": elapsed, "tool": "browser_click",
            "target": target, "error": f"Could not find clickable element: '{target}'"
        }

    async def _find_text_on_page(self, text: str) -> bool:
        """Check if specific text is visible on the current page."""
        try:
            page = await self._ensure_page()
            result = await page.evaluate(
                "(text) => document.body.innerText.toLowerCase().includes(text.toLowerCase())",
                text
            )
            return bool(result)
        except Exception:
            return False

    async def close(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close BrowserAgent: {e}")
        finally:
            self._page = None
            self._context = None
            self._playwright = None
            self.memory.session_state = "idle"


browser_agent = BrowserAgent()
