"""
provider/facade.py
==================
Nexus Provider Domain — ProviderAgent Facade

Single Responsibility: Public API surface for the provider domain.
Orchestrates multi-LLM routing and rate-limit governance.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.provider.router import model_router, ModelRouter, TaskClass, AgentTier
from core.provider.governor import governor, ProviderGovernor

logger = logging.getLogger("nexus.provider.facade")

class ProviderAgent:
    """
    Public facade for the Nexus provider domain.
    Delegates inference requests to the ModelRouter and enforces limits via ProviderGovernor.
    """
    
    @property
    def router(self) -> ModelRouter:
        return model_router
        
    @property
    def governor(self) -> ProviderGovernor:
        return governor

    # --- Router Pass-throughs ---
    async def route_task(
        self,
        task_class: TaskClass,
        system_prompt: str,
        messages: List[Dict[str, str]],
        force_model: Optional[str] = None,
    ) -> str:
        return await model_router.route_task(task_class, system_prompt, messages, force_model)

    async def standard_chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
    ) -> str:
        return await model_router.standard_chat(system_prompt, messages, model)

    async def execute_tool_call(
        self,
        user_intent: str,
        available_tools: List[Dict[str, Any]],
        model: str = "llama-3.3-70b-versatile",
    ) -> Dict[str, Any]:
        return await model_router.execute_tool_call(user_intent, available_tools, model)

    # --- Governor Pass-throughs ---
    async def wait_if_needed(self, provider: str, estimated_tokens: int = 0) -> None:
        await governor.wait_if_needed(provider, estimated_tokens)

provider_agent = ProviderAgent()
