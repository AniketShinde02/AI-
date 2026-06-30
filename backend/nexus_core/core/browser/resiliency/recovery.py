"""
browser/resiliency/recovery.py
================================
Nexus Browser Domain — Smart Recovery Pipeline (V3 Engine)
"""
from __future__ import annotations

import logging
import asyncio
import time
from typing import Any, Dict

from core.browser.models import BrowserStep

logger = logging.getLogger("nexus.browser.resiliency.recovery")

class SmartRecoveryPipeline:
    """
    Executes a multi-stage deterministic recovery process for a failed BrowserStep.
    Does NOT query the LLM.
    """
    async def attempt_recovery(self, step: BrowserStep, page: Any, session: Any, action_engine: Any, extractor: Any) -> Dict[str, Any]:
        logger.info(f"🔄 [RecoveryPipeline] Initiating recovery for step: {step.action}({step.target})")
        start = time.perf_counter()
        last_error = "Unknown"

        # 1. Immediate Retry with slight jitter
        logger.debug("[Recovery] Stage 1: Immediate Retry")
        await asyncio.sleep(1.0)
        res = await self._dispatch(step, page, session, action_engine)
        if res.get("success"):
            return self._success(res, 1, start)
            
        # 2. Wait for network idle and retry
        logger.debug("[Recovery] Stage 2: Wait for network idle")
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        res = await self._dispatch(step, page, session, action_engine)
        if res.get("success"):
            return self._success(res, 2, start)

        # 3. Try alternative targets (if provided by plan)
        if step.alt_targets:
            logger.debug(f"[Recovery] Stage 3: Attempting {len(step.alt_targets)} alt targets")
            for alt in step.alt_targets:
                logger.debug(f"  Trying alt target: {alt}")
                alt_step = BrowserStep(action=step.action, target=alt, value=step.value, alt_targets=[])
                res = await self._dispatch(alt_step, page, session, action_engine)
                if res.get("success"):
                    return self._success(res, 3, start)

        # 4. Try fuzzy text matching / ARIA (delegated to action_engine/locator_engine)
        logger.debug("[Recovery] Stage 4: Fuzzy Text / ARIA Matching")
        if step.action in {"click", "type"} and not step.target.startswith("text="):
            # Try to click by text if the target was a selector, or vice versa
            # The locator engine will handle ARIA roles automatically if we pass a special flag, 
            # but for now we'll just rewrite the target to be a fuzzy text search if it's alphanumeric.
            if step.target.replace(" ", "").isalnum():
                alt_step = BrowserStep(action=step.action, target=f"text={step.target}", value=step.value)
                res = await self._dispatch(alt_step, page, session, action_engine)
                if res.get("success"):
                    return self._success(res, 4, start)

        elapsed = f"{time.perf_counter() - start:.2f}s"
        logger.error(f"❌ [RecoveryPipeline] All stages exhausted for {step.action}")
        return {"success": False, "verified": False, "error": "Recovery exhausted", "recovery_level_used": 5, "execution_time": elapsed}

    def _success(self, res: Dict[str, Any], level: int, start: float) -> Dict[str, Any]:
        res["recovery_level_used"] = level
        res["execution_time"] = f"{time.perf_counter() - start:.2f}s"
        logger.info(f"✅ [RecoveryPipeline] Recovered successfully at Stage {level} in {res['execution_time']}")
        return res

    async def _dispatch(self, step: BrowserStep, page: Any, session: Any, action_engine: Any) -> Dict[str, Any]:
        if step.action == "open_url": return await action_engine.open_url(page, session, step.target)
        if step.action == "click": return await action_engine.click(page, session, step.target)
        if step.action == "type": return await action_engine.type_text(page, session, step.target, step.value)
        if step.action == "search": return await action_engine.search(page, session, step.target)
        return {"success": False, "error": "Unsupported action"}

smart_recovery_pipeline = SmartRecoveryPipeline()
