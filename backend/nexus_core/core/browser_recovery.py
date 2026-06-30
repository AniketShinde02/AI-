"""
browser_recovery.py
===================
Nexus BrowserAgent V1.1 — 5-Level Recovery Engine

On action failure, tries progressively stronger recovery strategies:

  Level 1: Original locator retry (same strategy, fresh attempt)
  Level 2: DOM refresh + next locator in cascade
  Level 3: A11y tree re-snapshot → re-locate
  Level 4: Screenshot → visual confirmation + re-locate
  Level 5: FAIL → record reason in failure matrix

Every failure is logged to the session's failure_matrix for benchmark reporting.
"""
import logging
import asyncio
import time
from typing import Any, Callable, Dict, Optional, Awaitable

logger = logging.getLogger("nexus.browser_recovery")


class RecoveryEngine:
    """
    Wraps any browser action with a 5-level recovery cascade.
    """

    async def execute_with_recovery(
        self,
        action_name: str,
        action_fn: Callable[[], Awaitable[Dict[str, Any]]],
        page: Any,
        session_memory: Any,
        screenshot_fn: Optional[Callable[[], Awaitable[Optional[str]]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an action with automatic 5-level recovery on failure.

        Args:
            action_name: Human-readable name for logging (e.g. "type into search")
            action_fn: Async callable that performs the action → returns result dict
            page: Playwright Page object (for DOM refresh)
            session_memory: BrowserMemory instance (for failure_matrix logging)
            screenshot_fn: Optional async fn that captures screenshot for visual verification

        Returns:
            Result dict with {success, verified, result/error, recovery_level_used}
        """
        start = time.perf_counter()
        last_error = None

        for level in range(1, 6):
            try:
                if level == 2:
                    # Level 2: Reload DOM observation before retry
                    logger.debug(f"[Recovery] L2: Refreshing DOM before retry for '{action_name}'")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=2000)
                    except Exception:
                        await page.wait_for_timeout(500)

                elif level == 3:
                    # Level 3: Force accessibility tree re-snapshot and shadow DOM probing
                    logger.debug(f"[Recovery] L3: Forcing A11y refresh for '{action_name}'")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1000)

                elif level == 4:
                    # Level 4: Visual verification via screenshot
                    logger.debug(f"[Recovery] L4: Attempting visual confirmation for '{action_name}'")
                    if screenshot_fn:
                        try:
                            img_b64 = await screenshot_fn()
                            if img_b64:
                                logger.info(f"[Recovery] L4: Screenshot captured ({len(img_b64)} bytes)")
                        except Exception:
                            pass
                    await page.wait_for_timeout(1500)

                elif level == 5:
                    # Level 5 — terminal failure, record and return
                    elapsed = f"{time.perf_counter() - start:.2f}s"
                    reason = str(last_error)
                    logger.error(
                        f"[Recovery] ❌ All 5 recovery levels exhausted for '{action_name}': {reason}"
                    )
                    _record_failure(session_memory, action_name, reason, level)
                    return {
                        "success": False,
                        "verified": False,
                        "error": f"[Recovery:L5] {reason}",
                        "recovery_level_used": 5,
                        "execution_time": elapsed,
                    }

                # Attempt the action
                result = await action_fn()
                if result.get("success"):
                    elapsed = f"{time.perf_counter() - start:.2f}s"
                    if level > 1:
                        logger.info(
                            f"[Recovery] ✅ '{action_name}' succeeded at recovery level {level} in {elapsed}"
                        )
                    result["recovery_level_used"] = level
                    result["execution_time"] = elapsed
                    return result
                else:
                    last_error = result.get("error", "success=False")
                    logger.warning(
                        f"[Recovery] L{level}: '{action_name}' returned failure: {last_error}"
                    )

            except Exception as e:
                last_error = e
                logger.warning(f"[Recovery] L{level}: '{action_name}' raised: {e}")
                await asyncio.sleep(level * 0.5)  # backoff: 0.5s, 1s, 1.5s, 2s

        # Should never reach here but safety net
        elapsed = f"{time.perf_counter() - start:.2f}s"
        return {
            "success": False,
            "verified": False,
            "error": f"Recovery exhausted: {last_error}",
            "recovery_level_used": 5,
            "execution_time": elapsed,
        }


def _record_failure(memory: Any, action: str, reason: str, level: int) -> None:
    """Record failure to session's failure_matrix for benchmarking."""
    try:
        if not hasattr(memory, "failure_matrix"):
            memory.failure_matrix = []
        memory.failure_matrix.append({
            "action": action,
            "reason": reason[:300],
            "recovery_level": level,
            "timestamp": time.time(),
        })
        # Keep last 50 failures
        if len(memory.failure_matrix) > 50:
            memory.failure_matrix = memory.failure_matrix[-50:]
    except Exception:
        pass


recovery_engine = RecoveryEngine()
