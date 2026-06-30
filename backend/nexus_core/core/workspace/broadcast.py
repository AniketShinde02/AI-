import logging
from typing import Optional, Dict, Any
from core.workspace.workspace_manager import workspace_manager

logger = logging.getLogger("nexus.broadcast")

async def broadcast_workspace_state(
    active_capability: Optional[str] = None,
    status: str = "idle",
    verification_state: Optional[str] = None,
    current_task: Optional[str] = None,
    tool_target: Optional[str] = None,
    execution_time: Optional[str] = None,
    last_result: Optional[str] = None,
    browser_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Broadcast current workspace state to all active client WebSocket sessions."""
    try:
        import core.global_state as gs
        if not gs.active_sessions:
            return

        workspace_manager.update_execution(
            status=status,
            active_capability=active_capability,
            verification_state=verification_state,
            last_result=last_result,
            execution_time=execution_time,
            current_task=current_task,
        )

        for session in list(gs.active_sessions.values()):
            if not session.is_connected:
                continue

            ws_state = await workspace_manager.get(session.session_id)

            broadcast_dict = ws_state.to_broadcast_dict()
            if current_task:
                broadcast_dict["current_task"] = current_task
            if tool_target:
                broadcast_dict["tool_target"] = tool_target
            if browser_state:
                broadcast_dict["browser_memory"] = browser_state

            payload = {"type": "workspace_state", "data": broadcast_dict}
            await session.safe_send_json(payload)
    except Exception as e:
        logger.error(f"❌ Failed to broadcast workspace state: {e}", exc_info=True)

async def broadcast_screencast_frame(session_id: str, frame_b64: str) -> None:
    """Broadcast a screencast frame to the frontend."""
    try:
        import core.global_state as gs
        session = gs.active_sessions.get(session_id)
        if session and session.is_connected:
            await session.safe_send_json({
                "type": "screencast_frame",
                "data": frame_b64
            })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast screencast frame: {e}")
