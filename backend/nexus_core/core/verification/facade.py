"""
verification/facade.py
======================
Nexus Verification Domain — VerificationAgent Facade

Single Responsibility: Public API surface for the verification domain.
Orchestrates guardrails and visual/matrix outcome verifications.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from core.verification.matrix import verification_engine, VerificationEngine, verify_feature, get_all_verifications, verify_feature_sync
from core.verification.guardrails import guardrails, GuardrailPolicyEngine

logger = logging.getLogger("nexus.verification.facade")

class VerificationAgent:
    """
    Public facade for the Nexus verification domain.
    Delegates checks to the Guardrails and Verification engines.
    """
    
    @property
    def engine(self) -> VerificationEngine:
        return verification_engine
        
    @property
    def guardrails(self) -> GuardrailPolicyEngine:
        return guardrails

    # --- Matrix Pass-throughs ---
    async def verify_action(self, tool_id: str, target: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        return await verification_engine.verify_action(tool_id, target, contract)
        
    async def verify_feature(self, feature: str, status: str, result: str, evidence: str) -> None:
        await verify_feature(feature, status, result, evidence)
        
    async def get_all_verifications(self) -> list:
        return await get_all_verifications()
        
    def verify_feature_sync(self, feature: str, status: str, result: str, evidence: str) -> None:
        verify_feature_sync(feature, status, result, evidence)

    # --- Guardrails Pass-throughs ---
    def scan_command(self, command: str) -> Tuple[str, str]:
        return guardrails.scan_command(command)
        
    async def request_authorization(self, session_id: str, command: str) -> bool:
        return await guardrails.request_authorization(session_id, command)
        
    def authorize_action(self, session_id: str, approved: bool) -> None:
        guardrails.authorize_action(session_id, approved)

verification_agent = VerificationAgent()
