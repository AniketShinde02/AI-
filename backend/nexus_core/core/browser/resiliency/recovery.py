"""
browser/resiliency/recovery.py
================================
Nexus Browser Domain — 5-Level Recovery Engine

Single Responsibility: Wrap any async browser action with an automatic 5-level
recovery cascade using smart Playwright waits (not asyncio.sleep).

Level 1: Original retry
Level 2: wait_for domcontentloaded → retry
Level 3: wait_for networkidle + 1s → retry
Level 4: Screenshot visual confirmation → retry
Level 5: Terminal failure → record in failure_matrix
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("nexus.browser.resiliency.recovery")


class RecoveryEngine:
    """Wrap any browser action with a 5-level smart-wait recovery cascade."""

    async def execute_with_recovery(
        self,
        action_name: str,
        action_fn: Callable[[], Awaitable[Dict[str, Any]]],
        page: Any,
        session_memory: Any,
        screenshot_fn: Optional[Callable[[], Awaitable[Optional[str]]]] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        last_error: Any = None

        for level in range(1, 6):
            try:
                if level == 2:
                    logger.debug(f"[Recovery] L2: DOM refresh before '{action_name}'")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=2000)
                    except Exception:
                        await page.wait_for_timeout(500)

                elif level == 3:
                    logger.debug(f"[Recovery] L3: Network idle + A11y refresh for '{action_name}'")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1000)

                elif level == 4:
                    logger.debug(f"[Recovery] L4: Visual screenshot for '{action_name}'")
                    if screenshot_fn:
                        try:
                            img_b64 = await screenshot_fn()
                            if img_b64:
                                logger.info(f"[Recovery] L4: Screenshot captured ({len(img_b64)} bytes)")
                        except Exception:
                            pass
                    await page.wait_for_timeout(1500)

                elif level == 5:
                    elapsed = f"{time.perf_counter() - start:.2f}s"
                    reason = str(last_error)
                    logger.error(f"[Recovery] ❌ All 5 levels exhausted for '{action_name}': {reason}")
                    _record_failure(session_memory, action_name, reason, level)
                    return {
                        "success": False, "verified": False,
                        "error": f"[Recovery:L5] {reason}",
                        "recovery_level_used": 5,
                        "execution_time": elapsed,
                    }

                result = await action_fn()
                if result.get("success"):
                    elapsed = f"{time.perf_counter() - start:.2f}s"
                    if level > 1:
                        logger.info(f"[Recovery] ✅ '{action_name}' succeeded at L{level} in {elapsed}")
                    result["recovery_level_used"] = level
                    result["execution_time"] = elapsed
                    return result
                else:
                    last_error = result.get("error", "success=False")
                    logger.warning(f"[Recovery] L{level}: '{action_name}' → {last_error}")

            except Exception as e:
                last_error = e
                logger.warning(f"[Recovery] L{level}: '{action_name}' raised: {e}")
                await page.wait_for_timeout(int(level * 500))

        elapsed = f"{time.perf_counter() - start:.2f}s"
        return {
            "success": False, "verified": False,
            "error": f"Recovery exhausted: {last_error}",
            "recovery_level_used": 5,
            "execution_time": elapsed,
        }


def _record_failure(memory: Any, action: str, reason: str, level: int) -> None:
    try:
        if not hasattr(memory, "failure_matrix"):
            memory.failure_matrix = []
        memory.failure_matrix.append({
            "action": action,
            "reason": reason[:300],
            "recovery_level": level,
            "timestamp": time.time(),
        })
        if len(memory.failure_matrix) > 50:
            memory.failure_matrix = memory.failure_matrix[-50:]
    except Exception:
        pass


recovery_engine = RecoveryEngine()
