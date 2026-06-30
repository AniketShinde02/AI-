"""
memory/facade.py
================
Nexus Memory Domain — MemoryAgent Facade

Single Responsibility: Public API surface for the memory domain.
Orchestrates LanceDB vector storage and RAG retrieval.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.memory.vector_store import get_memory, SemanticMemory
from core.memory.rag_engine import RAGOracle, oracle_instance

logger = logging.getLogger("nexus.memory.facade")

class MemoryAgent:
    """
    Public facade for the Nexus memory domain.
    Delegates retrieval and embedding to LanceDB and RAG engines.
    """
    
    async def get_vector_store(self) -> SemanticMemory:
        return await get_memory()
        
    @property
    def oracle(self) -> Optional[RAGOracle]:
        return oracle_instance
        
    async def ingest_codebase(self, dir_path: str) -> Dict[str, Any]:
        if not self.oracle:
            return {"success": False, "error": "RAG Oracle not initialized."}
        return await self.oracle.ingest_codebase(dir_path)
        
    async def consult_oracle(self, query: str) -> Dict[str, Any]:
        if not self.oracle:
            return {"success": False, "answer": "RAG Oracle not initialized."}
        return await self.oracle.consult_oracle(query)

memory_agent = MemoryAgent()
