import logging
from typing import Dict, Any, Optional, List
from core.database import db

logger = logging.getLogger("nexus.capabilities")

class CapabilityRegistry:
    def __init__(self):
        self.session_permissions = {} # user_id -> {capability_id -> state}

    async def register_tool(self, tool_id: str, name: str, description: str, category: str = "System", permissions_required: bool = False, requires_approval: bool = False, enabled: bool = True):
        """Register a tool with the central database."""
        await db.register_capability({
            "id": tool_id,
            "name": name,
            "description": description,
            "category": category,
            "permissions_required": permissions_required,
            "requires_approval": requires_approval,
            "enabled": enabled
        })
        logger.info(f"Registered tool capability: {tool_id} ({name})")

    async def check_permission(self, user_id: str, tool_id: str) -> str:
        """
        Check if a user has permission to execute a tool.
        Returns: 'Allow', 'Deny', or 'Prompt'
        """
        cap = await db.get_capability(tool_id)
        if not cap:
            logger.warning(f"Tool {tool_id} not found in registry.")
            return "Deny"

        if not cap["enabled"]:
            return "Deny"

        if not cap["permissions_required"]:
            return "Allow"

        # Check session override first (RAM)
        session_state = self.session_permissions.get(user_id, {}).get(tool_id)
        if session_state == "Allow Session":
            return "Allow"
        elif session_state == "Deny":
            return "Deny"

        # Check permanent state (SQLite)
        db_state = await db.get_user_permission(user_id, tool_id)
        
        if db_state == "Always Allow" and not cap["requires_approval"]:
            return "Allow"
        elif db_state == "Deny":
            return "Deny"

        # If we get here, we need the user to approve
        return "Prompt"

    def grant_session_permission(self, user_id: str, tool_id: str, state: str):
        """Grant a temporary session permission ('Allow Session' or 'Deny')"""
        if user_id not in self.session_permissions:
            self.session_permissions[user_id] = {}
        self.session_permissions[user_id][tool_id] = state

    async def log_execution(self, tool_id: str, parameters: Dict[str, Any], status: str, permission_state: str):
        """Log a tool execution to the audit log."""
        await db.log_tool_audit(tool_id, parameters, status, permission_state)

registry = CapabilityRegistry()
