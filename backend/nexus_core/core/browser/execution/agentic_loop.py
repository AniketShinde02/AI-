"""
browser/execution/agentic_loop.py
====================================
Nexus Browser Domain — LLM-Driven Agentic Loop

Single Responsibility: The Observe → Decide → Act → Verify loop that uses
the model_router to autonomously select the next action from DOM state.
Strictly delegates every action to ActionEngine. Never touches Playwright directly.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from core.browser.models import BrowserStateEnum
from core.browser.prompts import AGENTIC_SYSTEM_PROMPT

logger = logging.getLogger("nexus.browser.execution.agentic_loop")

_VALID_ACTIONS = {
    "open_url", "click", "type", "submit", "search", "wait",
    "verify_text", "verify_url", "scroll", "extract", "back",
    "forward", "refresh", "select", "done", "fail",
}


class AgenticLoop:
    """
    LLM-driven autonomous browser task executor.

    Depends on ActionEngine and PageExtractor — never imports Playwright.
    """

    async def run(
        self,
        goal: str,
        session: Any,
        page: Any,
        action_engine: Any,
        extractor: Any,
        update_memory_fn: Callable,
        max_iterations: int = 12,
        on_step_complete: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        from core.model_router import model_router, TaskClass

        session.memory.session_state = "interacting"
        logger.info(f"🤖 [AgenticLoop] Goal: '{goal}' | Max: {max_iterations} | Session: {session.session_id}")

        trace: List[Dict[str, Any]] = []
        history_lines: List[str] = []
        completed_iterations = 0
        last_fingerprint = ""
        stuck_count = 0

        for iteration in range(1, max_iterations + 1):
            logger.info(f"  [Iter {iteration}/{max_iterations}] Observing...")

            # ── OBSERVE ──────────────────────────────────────────────────
            await update_memory_fn()
            current_url = session.memory.current_url or "about:blank"
            current_title = session.memory.page_title or ""

            dom_result = await extractor.dom_snapshot(page)
            snap = dom_result.get("result", {})
            parts = []
            if snap.get("buttons"):
                parts.append("Buttons: " + " | ".join(
                    f"[{b.get('text','?')}]({b.get('selector','')})"
                    for b in snap["buttons"][:8]
                ))
            if snap.get("inputs"):
                parts.append("Inputs: " + " | ".join(
                    f"[{i.get('type','text')} name={i.get('name','')} id={i.get('id','')}]"
                    for i in snap["inputs"][:6]
                ))
            if snap.get("links"):
                parts.append("Links: " + " | ".join(
                    f"[{lk.get('text','?')}]({lk.get('href','')})"
                    for lk in snap["links"][:8] if lk.get("text")
                )[:400])
            if snap.get("text"):
                parts.append("Text: " + " / ".join(str(t)[:80] for t in snap["text"][:5]))

            current_state = (
                f"URL: {current_url}\n"
                f"Title: {current_title}\n"
                + ("\n".join(parts) if parts else "(no visible interactive elements)")
            )

            # Stuck-state detection
            fingerprint = f"{current_url}::{current_title}"
            if fingerprint == last_fingerprint and iteration > 3:
                stuck_count += 1
                if stuck_count >= 3:
                    logger.warning(f"  [AgenticLoop] Stuck state at '{current_url}'. Stopping.")
                    trace.append({"iteration": iteration, "observation": current_state,
                                   "action": None, "result": "STUCK_STATE", "success": False})
                    break
            else:
                stuck_count = 0
            last_fingerprint = fingerprint

            # ── DECIDE ───────────────────────────────────────────────────
            history_ctx = "\n".join(history_lines[-6:]) or "(no prior actions)"
            messages = [{"role": "user", "content": (
                f"GOAL: {goal}\n\nCURRENT STATE:\n{current_state}\n\n"
                f"HISTORY (last 6):\n{history_ctx}\n\n"
                "What is the NEXT single action? Reply with JSON only."
            )}]

            raw = ""
            try:
                raw = await model_router.route_task(
                    task_class=TaskClass.BROWSER,
                    system_prompt=AGENTIC_SYSTEM_PROMPT,
                    messages=messages,
                )
                clean = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
                decision = json.loads(clean.group(0) if clean else raw)
            except (json.JSONDecodeError, AttributeError):
                logger.warning(f"  [AgenticLoop] Non-JSON response: {raw[:200]}")
                trace.append({"iteration": iteration, "action": "PARSE_ERROR",
                               "result": raw, "success": False})
                break
            except Exception as e:
                logger.error(f"  [AgenticLoop] LLM error: {e}")
                trace.append({"iteration": iteration, "action": "LLM_ERROR",
                               "result": str(e), "success": False})
                break

            action  = decision.get("action", "")
            target  = decision.get("target", "")
            text    = decision.get("text", "")
            is_done = bool(decision.get("done", False))
            reason  = decision.get("reasoning", "")

            if action and action not in _VALID_ACTIONS:
                logger.warning(f"  [AgenticLoop] Invalid action '{action}' — rejected")
                history_lines.append(f"[{iteration}] INVALID_ACTION({action!r}) → ❌ rejected")
                continue

            logger.info(f"  [Iter {iteration}] {action}({target!r}) — {reason[:80]}")

            if is_done:
                trace.append({"iteration": iteration, "action": "DONE",
                               "result": reason, "success": True})
                completed_iterations = iteration
                break

            # ── ACT ───────────────────────────────────────────────────────
            step: Dict[str, Any] = {}
            try:
                if action == "open_url":
                    step = await action_engine.open_url(page, session, target)
                elif action == "click":
                    step = await action_engine.click(page, session, target)
                elif action == "type":
                    step = await action_engine.type_text(page, session, target, text)
                elif action == "submit":
                    step = await action_engine.submit(page, session, target or None)
                elif action == "search":
                    step = await action_engine.search(page, session, target)
                elif action == "wait":
                    secs = min(float(target) if target else 2.0, 10.0)
                    import asyncio
                    await asyncio.sleep(secs)
                    step = {"success": True, "verified": True, "result": f"Waited {secs}s"}
                elif action == "scroll":
                    step = await action_engine.scroll(page, session, target or "down")
                elif action == "verify_text":
                    found = await extractor.text_present(page, target)
                    step = {"success": found, "verified": found,
                            "result": f"Text '{target}' {'found' if found else 'NOT found'}"}
                else:
                    step = {"success": False, "verified": False,
                            "error": f"Unhandled action: '{action}'"}
            except Exception as e:
                step = {"success": False, "verified": False, "error": str(e)}
                logger.error(f"  [AgenticLoop] Action '{action}' raised: {e}")

            # ── VERIFY ────────────────────────────────────────────────────
            success = step.get("success", False)
            result_str = str(step.get("result", step.get("error", "")))[:200]
            history_lines.append(f"[{iteration}] {action}({target!r}) → {'✅' if success else '❌'} {result_str}")
            trace.append({
                "iteration": iteration,
                "observation": {"url": current_url, "title": current_title},
                "action": action, "target": target, "text": text,
                "reasoning": reason, "result": step, "success": success,
            })

            if on_step_complete:
                try:
                    await on_step_complete({"iteration": iteration, "action": action,
                                            "target": target, "success": success, "result": result_str})
                except Exception:
                    pass

            completed_iterations = iteration

        await update_memory_fn()
        session.memory.session_state = "completed"
        overall_success = any(t.get("action") == "DONE" for t in trace) or (
            completed_iterations > 0 and bool(trace) and trace[-1].get("success", False)
        )

        logger.info(f"🤖 [AgenticLoop] Done. Iterations: {completed_iterations}/{max_iterations}")
        return {
            "success": overall_success, "verified": overall_success,
            "goal": goal, "iterations_used": completed_iterations,
            "max_iterations": max_iterations,
            "final_url": session.memory.current_url,
            "final_title": session.memory.page_title,
            "trace": trace,
        }


agentic_loop = AgenticLoop()
