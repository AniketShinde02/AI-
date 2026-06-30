"""
verification/__init__.py
========================
Nexus Verification Domain — Public API
"""
from core.verification.facade import VerificationAgent, verification_agent
from core.verification.matrix import VerificationEngine, verification_engine, verify_feature, get_all_verifications, verify_feature_sync
from core.verification.guardrails import GuardrailPolicyEngine, guardrails

__all__ = [
    "VerificationAgent",
    "verification_agent",
    "VerificationEngine",
    "verification_engine",
    "verify_feature",
    "get_all_verifications",
    "verify_feature_sync",
    "GuardrailPolicyEngine",
    "guardrails"
]
