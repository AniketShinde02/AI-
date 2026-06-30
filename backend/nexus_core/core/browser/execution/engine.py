import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from core.browser.models import BrowserStateEnum, BrowserPlan
from core.browser.resiliency.recovery import smart_recovery_pipeline

logger = logging.getLogger("nexus.browser.execution.engine")

class ExecutionEngine:
    """
    NEXUS V3: Deterministic Execution Engine
    Executes a BrowserPlan sequentially, deferring to the Recovery Pipeline on failure.
    """
    
    async def run(
        self,
        plan: BrowserPlan,
        session: Any,
        page: Any,
        action_engine: Any,
        extractor: Any,
        update_memory_fn: Callable,
        on_step_complete: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        
        logger.info(f"🚀 [ExecutionEngine] Starting execution for goal: '{plan.goal}' ({len(plan.steps)} steps)")
        await session.state_machine.transition_to(BrowserStateEnum.EXECUTING)
        
        trace = []
        overall_success = True
        
        for step_idx, step in enumerate(plan.steps):
            logger.info(f"  [Step {step_idx+1}/{len(plan.steps)}] {step.action}({step.target})")
            
            # Emit Telemetry
            await self._emit_telemetry(session, plan.goal, step_idx + 1, step.action, step.target, status="started")
            
            step_start = time.perf_counter()
            result = {"success": False, "verified": False}
            
            # 1. Primary Execution Attempt
            try:
                result = await self._dispatch_action(step, page, session, action_engine)
            except Exception as e:
                logger.warning(f"⚠️ [ExecutionEngine] Primary execution failed for {step.action}: {e}")
                
            # 2. Smart Recovery Pipeline
            if not result.get("success") and not step.optional:
                logger.info(f"🔄 [ExecutionEngine] Triggering Recovery Pipeline for {step.action}...")
                await session.state_machine.transition_to(BrowserStateEnum.RECOVERING)
                
                result = await smart_recovery_pipeline.attempt_recovery(
                    step=step,
                    page=page,
                    session=session,
                    action_engine=action_engine,
                    extractor=extractor
                )
                
                await session.state_machine.transition_to(BrowserStateEnum.EXECUTING)

            elapsed_ms = int((time.perf_counter() - step_start) * 1000)
            
            # 3. Post-step Processing
            if result.get("success"):
                logger.info(f"✅ [ExecutionEngine] Step {step_idx+1} succeeded in {elapsed_ms}ms")
                await self._emit_telemetry(session, plan.goal, step_idx + 1, step.action, step.target, status="success", time_ms=elapsed_ms)
                trace.append({"step": step.to_dict(), "result": result, "success": True})
            else:
                if step.optional:
                    logger.info(f"⏭️ [ExecutionEngine] Step {step_idx+1} failed but was optional. Skipping.")
                    trace.append({"step": step.to_dict(), "result": result, "success": False, "skipped": True})
                else:
                    logger.error(f"❌ [ExecutionEngine] Step {step_idx+1} FATAL failure. Aborting plan.")
                    await self._emit_telemetry(session, plan.goal, step_idx + 1, step.action, step.target, status="failed", time_ms=elapsed_ms)
                    trace.append({"step": step.to_dict(), "result": result, "success": False})
                    overall_success = False
                    break
                    
            if on_step_complete:
                await on_step_complete(step, result)
                
            await update_memory_fn()

        if overall_success:
            await session.state_machine.transition_to(BrowserStateEnum.SUCCESS)
            return {"success": True, "trace": trace, "result": "Plan executed successfully."}
        else:
            await session.state_machine.transition_to(BrowserStateEnum.FAILED)
            return {"success": False, "trace": trace, "result": "Plan failed during execution."}

    async def _dispatch_action(self, step: Any, page: Any, session: Any, action_engine: Any) -> Dict[str, Any]:
        """Routes the BrowserStep to the appropriate ActionEngine method."""
        if step.action == "open_url":
            return await action_engine.open_url(page, session, step.target)
        elif step.action == "click":
            return await action_engine.click(page, session, step.target)
        elif step.action == "type":
            return await action_engine.type_text(page, session, step.target, step.value)
        elif step.action == "wait":
            # Wait for network idle or timeout
            try:
                if step.target == "networkidle":
                    await page.wait_for_load_state("networkidle", timeout=5000)
                else:
                    await asyncio.sleep(float(step.target))
                return {"success": True, "verified": True}
            except Exception:
                return {"success": True, "verified": True} # Wait is best effort
        elif step.action == "search":
            return await action_engine.search(page, session, step.target)
        elif step.action == "verify_media":
            from core.browser.verification import nav_verifier
            res = await nav_verifier.verify_media_playing(page)
            return {"success": res, "verified": res}
        # Add more mappings as needed (scroll, back, forward, extract)
        else:
            logger.warning(f"Unknown action '{step.action}' in dispatch.")
            return {"success": False, "error": f"Unknown action: {step.action}"}

    async def _emit_telemetry(self, session: Any, goal: str, step_num: int, action: str, target: str, status: str, time_ms: int = 0):
        try:
            import core.global_state as gs
            voice_session = gs.active_sessions.get(session.session_id)
            if voice_session and voice_session.is_connected:
                await voice_session.safe_send_json({
                    "type": "browser_telemetry",
                    "goal": goal,
                    "step": step_num,
                    "action": action,
                    "selector": target,
                    "status": status,
                    "elapsed_ms": time_ms
                })
        except Exception:
            pass

execution_engine = ExecutionEngine()
