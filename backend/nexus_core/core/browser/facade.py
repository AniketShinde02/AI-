"""
browser/facade.py
==================
Nexus Browser Domain — BrowserAgent Facade

Single Responsibility: Public API surface for the entire browser domain.
Orchestrates session, observation, execution, and agentic loop subpackages.
This class must never contain business logic — it only delegates.

Public methods mirror the original browser_agent.py interface 100% for
backward compatibility with voice_session, task_cards, executors, etc.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.browser.session.pool import session_pool
from core.browser.observation.extractor import page_extractor
from core.browser.execution.actions import action_engine
from core.browser.execution.planner import planner
from core.browser.execution.engine import execution_engine

logger = logging.getLogger("nexus.browser.facade")


class BrowserAgent:
    """
    Public facade for the Nexus browser domain.

    Usage:
        from core.browser import BrowserAgent
        agent = BrowserAgent()
        result = await agent.open_url("https://...", session_id="user_main")
    """

    # ------------------------------------------------------------------
    # Session lifecycle helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: Optional[str] = None):
        return session_pool.get_or_create(session_id)

    async def _ensure_page(self, session_id: Optional[str] = None):
        return await session_pool.ensure_page(session_id)

    async def _update_memory_from_page(self, session_id: Optional[str] = None) -> None:
        """Sync BrowserMemory with current page state and persist to DB."""
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
            session.memory.record_navigation(session.memory.current_url)
        except Exception as e:
            logger.debug(f"Memory sync failed for {session_id}: {e}")

        try:
            from core.database import db
            asyncio.create_task(db.upsert_browser_session(
                session_id=session.session_id,
                current_url=session.memory.current_url,
                page_title=session.memory.page_title,
                last_action=session.memory.last_action,
                tab_count=session.memory.total_tabs,
                session_state=session.memory.session_state,
            ))
        except Exception as e:
            logger.debug(f"DB sync failed: {e}")

    def get_workspace_state(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._get_session(session_id).memory.to_dict()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    async def get_dom_snapshot(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        page = await self._ensure_page(session_id)
        return await page_extractor.dom_snapshot(page)

    async def get_accessibility_tree(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        page = await self._ensure_page(session_id)
        return await page_extractor.a11y_tree(page)

    async def get_screenshot_base64(self, session_id: Optional[str] = None) -> Optional[str]:
        session = self._get_session(session_id)
        if not session._page or session._page.is_closed():
            return None
        return await page_extractor.screenshot_b64(session._page)

    async def screenshot(self, url: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        import os
        session = self._get_session(session_id)
        try:
            page = await self._ensure_page(session_id)
            if url:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            path = os.path.join(os.path.expanduser("~"), f"nexus_screenshot_{session.session_id}.png")
            await page.screenshot(path=path)
            img_b64 = await page_extractor.screenshot_b64(page, quality=60)
            analysis = "(vision unavailable)"
            try:
                from core.vision.parser import vision_parser
                analysis = await vision_parser.analyze_screenshot(
                    img_b64 or "", prompt="Describe the current webpage. What UI elements are visible?", use_som=False
                )
            except Exception as e:
                analysis = f"Vision failed: {e}"
            await self._update_memory_from_page(session_id)
            return {"success": True, "verified": True, "result": f"Screenshot saved to {path} | Vision: {analysis}"}
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

    async def observe(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        dom = await self.get_dom_snapshot(session_id)
        await self._update_memory_from_page(session_id)
        return {
            "success": True, "verified": True,
            "url": session.memory.current_url,
            "title": session.memory.page_title,
            "dom": dom.get("result", {}),
            "memory": session.memory.to_dict(),
        }

    # ------------------------------------------------------------------
    # Screencast
    # ------------------------------------------------------------------

    async def start_screencast(self, on_frame: Callable[[str], Awaitable[None]], session_id: Optional[str] = None) -> None:
        from core.browser.session.streaming import streamer
        page = await self._ensure_page(session_id)
        await streamer.start_screencast(page, on_frame)

    async def stop_screencast(self) -> None:
        from core.browser.session.streaming import streamer
        await streamer.stop_screencast()

    # ------------------------------------------------------------------
    # Input Passthrough (Screencast / Interactive)
    # ------------------------------------------------------------------

    async def cdp_mouse_click(self, x: int, y: int, button: str = "left", session_id: Optional[str] = None) -> None:
        from core.browser.session.streaming import streamer
        if streamer.cdp_session:
            await streamer.cdp_session.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": 1
            })
            await streamer.cdp_session.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": 1
            })

    async def cdp_mouse_move(self, x: int, y: int, session_id: Optional[str] = None) -> None:
        from core.browser.session.streaming import streamer
        if streamer.cdp_session:
            await streamer.cdp_session.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": x,
                "y": y
            })

    async def cdp_keyboard_type(self, text: str, session_id: Optional[str] = None) -> None:
        from core.browser.session.streaming import streamer
        if streamer.cdp_session:
            for char in text:
                await streamer.cdp_session.send("Input.dispatchKeyEvent", {
                    "type": "char",
                    "text": char
                })

    async def cdp_keyboard_press(self, key: str, session_id: Optional[str] = None) -> None:
        page = await self._ensure_page(session_id)
        await page.keyboard.press(key)

    # ------------------------------------------------------------------
    # Actions — fully delegated to ActionEngine
    # ------------------------------------------------------------------

    async def open_url(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        result = await action_engine.open_url(page, session, url)
        await self._update_memory_from_page(session_id)
        return result

    async def search(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        result = await action_engine.search(page, session, query)
        await self._update_memory_from_page(session_id)
        return result

    async def click(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        result = await action_engine.click(page, session, selector)
        await self._update_memory_from_page(session_id)
        return result

    async def _smart_click(self, target: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await self.click(target, session_id)

    async def browser_type(self, selector: str, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        return await action_engine.type_text(page, session, selector, text)

    async def browser_submit(self, selector: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        result = await action_engine.submit(page, session, selector)
        await self._update_memory_from_page(session_id)
        return result

    async def infinite_scroll(self, max_iterations: int = 5, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        result = await action_engine.infinite_scroll(page, session, max_iterations)
        await self._update_memory_from_page(session_id)
        return result

    async def extract(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            page = await self._ensure_page(session_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._update_memory_from_page(session_id)
            text = await page_extractor.page_text(page)
            return {"success": True, "verified": True, "tool": "browser_extract", "target": url, "result": text}
        except Exception as e:
            return {"success": False, "verified": False, "tool": "browser_extract", "target": url, "error": str(e)}

    async def download(self, target_selector: str, dest: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        return await action_engine.download(page, session, target_selector, dest)

    async def upload(self, selector: str, file_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        return await action_engine.upload(page, session, selector, file_path)

    async def browser_tab_management(self, action: str, target: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        session = self._get_session(session_id)
        await self._ensure_page(session_id)
        result = await action_engine.manage_tabs(session._page, session, action, target)
        await self._update_memory_from_page(session_id)
        return result

    async def _find_text_on_page(self, text: str, session_id: Optional[str] = None) -> bool:
        page = await self._ensure_page(session_id)
        return await page_extractor.text_present(page, text)

    # ------------------------------------------------------------------
    # High-level task runners
    # ------------------------------------------------------------------

    async def run_browser_task(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        on_step_complete: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a caller-defined multi-step plan."""
        session = self._get_session(session_id)
        logger.info(f"🤖 [BrowserTask] Goal: '{goal}' | Steps: {len(steps)} | Session: {session.session_id}")
        session.memory.session_state = "interacting"

        results, completed = [], 0
        for i, step in enumerate(steps):
            action = step.get("action", "")
            target = step.get("target", "")
            text   = step.get("text", "")
            observation = await self.observe(session_id)
            step_result: Dict[str, Any] = {}
            for attempt in range(1, 4):
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
                        step_result = {"success": found, "verified": found, "result": f"URL {'contains' if found else 'does not contain'} '{target}'"}
                    elif action == "verify_text":
                        found = await self._find_text_on_page(target, session_id)
                        step_result = {"success": found, "verified": found, "result": f"Text '{target}' {'found' if found else 'NOT found'}"}
                    else:
                        step_result = {"success": False, "verified": False, "error": f"Unknown action: {action}"}
                        break
                    if step_result.get("success"):
                        break
                    raise Exception(step_result.get("error", "success=False"))
                except Exception as e:
                    step_result = {"success": False, "verified": False, "error": str(e)}
                    if attempt < 3:
                        await asyncio.sleep(attempt * 1.5)
                        observation = await self.observe(session_id)

            step_result.update({"step": i+1, "action": action, "target": target,
                                 "observation_before": {"url": observation.get("url"), "title": observation.get("title")}})
            results.append(step_result)
            if step_result.get("success"):
                completed += 1
            if on_step_complete:
                try:
                    await on_step_complete(step_result)
                except Exception:
                    pass
            if not step_result.get("success") and step.get("stop_on_fail", False):
                break

        await self._update_memory_from_page(session_id)
        session.memory.session_state = "completed" if completed == len(steps) else "error"
        return {
            "success": completed > 0 and completed == len(steps),
            "verified": completed > 0 and completed == len(steps),
            "goal": goal, "steps_completed": completed, "steps_total": len(steps),
            "final_url": session.memory.current_url, "final_title": session.memory.page_title,
            "results": results,
        }

    async def run_agentic_task(
        self,
        goal: str,
        session_id: Optional[str] = None,
        max_iterations: int = 12,
        on_step_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """NEXUS V3: Deterministic Planner and Execution Engine."""
        session = self._get_session(session_id)
        page = await self._ensure_page(session_id)
        
        # 1. Generate Deterministic Plan
        plan = await planner.plan(goal=goal, page=page, extractor=page_extractor)
        
        # 2. Execute Plan Sequentially
        return await execution_engine.run(
            plan=plan, 
            session=session, 
            page=page,
            action_engine=action_engine, 
            extractor=page_extractor,
            update_memory_fn=lambda: self._update_memory_from_page(session_id),
            on_step_complete=on_step_complete,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self, session_id: Optional[str] = None) -> None:
        await session_pool.close(session_id)
browser_agent = BrowserAgent()
