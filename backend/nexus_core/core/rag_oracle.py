"""
rag_oracle.py — Backward Compatibility Shim
===========================================
DO NOT add logic here. All behavior lives in core/memory/rag_engine.py.
"""
from core.memory.rag_engine import RAGOracle, oracle_instance

__all__ = ["RAGOracle", "oracle_instance"]
