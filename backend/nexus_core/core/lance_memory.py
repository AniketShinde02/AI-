"""
lance_memory.py — Backward Compatibility Shim
=============================================
DO NOT add logic here. All behavior lives in core/memory/vector_store.py.
"""
from core.memory.vector_store import SemanticMemory, get_memory

__all__ = ["SemanticMemory", "get_memory"]
