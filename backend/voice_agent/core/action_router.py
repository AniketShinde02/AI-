import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("nexus.action_router")

class ActionRouter:
    """
    Intercepts raw user intents before hitting LLM.
    Pattern matches direct app/tool invocations and immediately fires the tool without querying an LLM, reducing latency to zero.
    """
    
    def __init__(self):
        # Dynamic App Discovery handles resolution
        pass

    async def route_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Returns a dict with tool extraction if a direct action is matched.
        Otherwise returns None, meaning "pass this to the LLM".
        """
        text_lower = text.lower().strip()
        
        # 1. Check for APP OPEN intent
        open_match = re.match(r'^(?:can you )?(?:please )?open\s+(.*)', text_lower)
        if open_match:
            app_name = open_match.group(1).strip(".!?")
            return {
                "intent": "ACTION",
                "tool": "pc_open_app",
                "target": app_name
            }
            
        # 2. Check for APP CLOSE intent
        close_match = re.match(r'^(?:can you )?(?:please )?close\s+(.*)', text_lower)
        if close_match:
            app_name = close_match.group(1).strip(".!?")
            return {
                "intent": "ACTION",
                "tool": "pc_close_app",
                "target": app_name
            }

        # 3. Check for SCREENSHOT intent
        if re.match(r'^(?:take a )?screenshot', text_lower):
            return {
                "intent": "ACTION",
                "tool": "pc_take_screenshot",
                "target": "Screen"
            }

        # No deterministic action matched, fallback to standard LLM pipeline
        return None

action_router = ActionRouter()
