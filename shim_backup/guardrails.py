"""
guardrails.py — Backward Compatibility Shim
===========================================
DO NOT add logic here. All behavior lives in core/verification/guardrails.py.
"""
from core.verification.guardrails import guardrails, GuardrailPolicyEngine

__all__ = ["guardrails", "GuardrailPolicyEngine"]
