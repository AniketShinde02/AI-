from typing import Dict, Any, List
from core.executors.base import BaseExecutor
from core.desktop.control import pc_controller

class VisionExecutor(BaseExecutor):
    def get_capabilities(self) -> List[str]:
        return ["vision_analyze_screen"]

    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Routes vision capabilities."""
        if capability == "vision_analyze_screen":
            # pc_controller currently handles this in V1
            return await pc_controller.analyze_screen(params.get("query", ""), session_id=params.get("session_id"))
            
        return {"success": False, "verified": False, "error": f"Unknown vision capability {capability}"}
