import time
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.database import db
from core.workspace import workspace_manager

logger = logging.getLogger("nexus.executors")


class BaseExecutor(ABC):
    """
    Base executor for all Nexus V1.6 execution domains.
    Provides standardized capability ownership, execution hooks, retries, and verification.
    """
    def __init__(self):
        self.workspace = workspace_manager

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Returns a list of capability IDs owned by this executor."""
        pass

    @abstractmethod
    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core logic for execution.
        Must return a dict matching the contract:
        {"success": bool, "verified": bool, "result": str, "error": str}
        """
        pass
        
    async def _broadcast_state(self, capability: str, status: str, verification_state: str, target: str, result: str = "", execution_time: Optional[str] = None):
        """Internal helper to broadcast state to UI/System via WorkspaceManager."""
        self.workspace.update_execution(
            status=status,
            active_capability=capability,
            verification_state=verification_state,
            last_result=result,
            execution_time=execution_time
        )
        
        try:
            import core.global_state as gs
            if not gs.active_sessions:
                return
                
            for session in list(gs.active_sessions.values()):
                if not session.is_connected:
                    continue
                
                ws_state = await self.workspace.get(session.session_id)
                broadcast_dict = ws_state.to_broadcast_dict()
                if target:
                    broadcast_dict["tool_target"] = target
                    
                payload = {"type": "workspace_state", "data": broadcast_dict}
                await session.safe_send_json(payload)
        except Exception as e:
            logger.error(f"❌ Failed to broadcast workspace state: {e}", exc_info=True)

    def _validate_contract(self, raw_result: Dict[str, Any], tool_id: str) -> Dict[str, Any]:
        """Ensures the response dict conforms to the system contract."""
        if not isinstance(raw_result, dict):
            return {
                "success": False, "verified": False,
                "error": f"Invalid return type {type(raw_result)} from {tool_id}",
                "result": None, "tool": tool_id
            }
        raw_result.setdefault("success", False)
        raw_result.setdefault("verified", False)
        raw_result.setdefault("error", None)
        raw_result.setdefault("result", None)
        return raw_result

    async def run(self, capability: str, params: Dict[str, Any], max_retries: int = 3, visual_verification: bool = False) -> Dict[str, Any]:
        """
        The entrypoint for the Execution Engine. Wraps the `execute` method with:
        - Exponential backoff retries
        - Verification hooking
        - State broadcasting
        - Database logging
        """
        target: str = params.get("target") or params.get("url") or params.get("selector") or ""
        
        await self._broadcast_state(capability, "running", "pending", target)

        t_start = time.perf_counter()
        raw_result: Dict[str, Any] = {"success": False, "verified": False, "error": None, "result": ""}
        last_exception: Optional[str] = None

        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1:
                    logger.info(f"🔧 [Executor] '{capability}' → target='{target}'")
                else:
                    backoff = 1 * (attempt - 1)
                    logger.warning(
                        f"♻️  [Executor] RETRY {attempt - 1}/{max_retries - 1} for '{capability}' "
                        f"after: {last_exception!r} — waiting {backoff}s…"
                    )
                    await self._broadcast_state(capability, "retrying", "pending", target)
                    await asyncio.sleep(backoff)

                raw_result = await self.execute(capability, params)

                if raw_result is None:
                    raw_result = {"success": False, "verified": False, "error": "Executor returned None"}

                if raw_result.get("success") and raw_result.get("verified"):
                    if attempt > 1:
                        logger.info(f"✅ [Executor] '{capability}' self-healed on attempt {attempt}/{max_retries}")
                    break

                if raw_result.get("success") and not raw_result.get("verified"):
                    last_exception = raw_result.get("error") or "Execution succeeded but Verification failed."
                    raw_result["success"] = False 
                else:
                    last_exception = raw_result.get("error") or "Tool reported success=False"
                    
                logger.warning(f"⚠️  [Executor] Attempt {attempt}/{max_retries} for '{capability}' returned success=False: {last_exception}")

            except Exception as e:
                last_exception = f"{type(e).__name__}: {e}"
                raw_result = {"success": False, "verified": False, "error": last_exception, "result": ""}
                if attempt < max_retries:
                    logger.warning(f"⚠️  [Executor] Attempt {attempt}/{max_retries} for '{capability}' raised: {last_exception}")
                else:
                    logger.error(f"❌ [Executor] All {max_retries} attempts exhausted for '{capability}'. Last error: {last_exception}", exc_info=True)

        elapsed = time.perf_counter() - t_start
        raw_result["execution_time"] = f"{elapsed:.2f}s"
        raw_result.setdefault("tool", capability)
        raw_result.setdefault("target", target)

        contract = self._validate_contract(raw_result, capability)
        
        # Visual Verification
        if visual_verification and contract.get("success") and not contract.get("verified"):
            try:
                from core.verification_matrix import verification_engine
                logger.info(f"📸 [Executor] Running Visual Verification for '{capability}'...")
                vision_result = await verification_engine.verify_action(capability, target, contract)
                if vision_result.get("verified"):
                    contract["verified"] = True
                    contract["result"] = f"{contract.get('result', '')} [Vision: Verified]"
                else:
                    contract["verified"] = False
                    contract["success"] = False
                    contract["error"] = f"{contract.get('error', '')} [Vision Failed: {vision_result.get('reason')}]"
            except Exception as e:
                logger.error(f"Visual verification crashed: {e}")

        # DB Write
        asyncio.create_task(db.log_verification(
            capability, 
            "success" if contract.get("success") else "error", 
            str(contract), 
            str(contract.get("result", ""))
        ))

        status_emoji = "✅" if contract.get("success") else "❌"
        logger.info(f"{status_emoji} [Executor] '{capability}' → success={contract['success']} verified={contract['verified']} time={contract['execution_time']}")

        v_state = "passed" if contract.get("success") and contract.get("verified") else "failed"
        status_state = "completed" if contract.get("success") else "failed"
        result_summary = str(contract.get("result") or contract.get("error") or "")[:200]
        
        await self._broadcast_state(
            capability=capability,
            status=status_state,
            verification_state=v_state,
            target=target,
            execution_time=contract.get("execution_time"),
            result=result_summary
        )

        return contract
