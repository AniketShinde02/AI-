"""
verification_matrix.py — Backward Compatibility Shim
====================================================
DO NOT add logic here. All behavior lives in core/verification/matrix.py.
"""
from core.verification.matrix import verification_engine, VerificationEngine, verify_feature, get_all_verifications, verify_feature_sync

__all__ = ["verification_engine", "VerificationEngine", "verify_feature", "get_all_verifications", "verify_feature_sync"]
