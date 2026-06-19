import logging
from typing import Callable, Dict, Any, List, Optional
import inspect
from datetime import datetime
import asyncio

logger = logging.getLogger("nexus.tools")

class ToolPermissionError(Exception):
    pass

class ToolRegistry:
    """
    Centralized Tool Registry for Nexus.
    Handles registering tools, permission checks, logging, and asynchronous execution.
    """
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._permissions: Dict[str, List[str]] = {} # e.g. {"run_command": ["admin"]}
        self._execution_log: List[Dict[str, Any]] = []

    def register(self, name: str, func: Callable, required_roles: Optional[List[str]] = None):
        """Register a new tool."""
        self._tools[name] = func
        if required_roles:
            self._permissions[name] = required_roles
        logger.info(f"🛠️ Registered Tool: {name} (Roles: {required_roles})")

    def has_permission(self, name: str, user_roles: List[str]) -> bool:
        """Check if user has permission to execute the tool."""
        required = self._permissions.get(name, [])
        if not required:
            return True # Public tool
        return any(role in required for role in user_roles)

    async def execute(self, name: str, args: Dict[str, Any], user_roles: Optional[List[str]] = None) -> Any:
        """Execute a tool asynchronously with permission checks and logging."""
        user_roles = user_roles or ["user"]
        
        if name not in self._tools:
            logger.error(f"❌ Tool execution failed: Tool '{name}' not found.")
            return {"error": f"Tool '{name}' not found."}

        if not self.has_permission(name, user_roles):
            logger.warning(f"⛔ Tool permission denied: '{name}' for roles {user_roles}")
            return {"error": f"Permission denied for tool '{name}'."}

        func = self._tools[name]
        start_time = datetime.utcnow()
        
        log_entry = {
            "tool": name,
            "args": args,
            "timestamp": start_time.isoformat(),
            "status": "started"
        }
        self._execution_log.append(log_entry)
        
        try:
            logger.info(f"⚙️ Executing {name} with {args}")
            if inspect.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = await asyncio.to_thread(func, **args)
            
            log_entry["status"] = "success"
            log_entry["completed_at"] = datetime.utcnow().isoformat()
            return result
        except Exception as e:
            logger.exception(f"❌ Tool '{name}' raised an error: {e}")
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            return {"error": str(e)}

    def get_registered_tools(self) -> List[str]:
        """List all registered tools."""
        return list(self._tools.keys())

# Global singleton registry
tool_registry = ToolRegistry()
