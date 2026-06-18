import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nexus.trace")

async def emit_trace(websocket, event_type: str, text: str, icon: str = "⚡", metadata: Optional[Dict[str, Any]] = None):
    """
    Emit a trace event over the WebSocket to the frontend.
    This fulfills Rule 9: Trace Must Become Reality.
    """
    if websocket is None:
        logger.debug(f"[Trace Mute] {event_type}: {text}")
        return

    from core.output_processor import output_processor
    clean_text = output_processor.filter_reasoning(text)
    if not clean_text:
        return

    payload: Dict[str, Any] = {
        "type": "trace_event",
        "event_type": event_type,
        "text": clean_text,
        "icon": icon,
        "timestamp": int(time.time() * 1000)
    }
    
    if metadata:
        payload["metadata"] = metadata

    try:
        from starlette.websockets import WebSocketState
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(payload)
    except Exception as e:
        logger.error(f"Failed to emit trace event '{event_type}': {e}")
