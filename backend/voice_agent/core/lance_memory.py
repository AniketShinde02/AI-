import os
import lancedb
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger("nexus.lance_memory")

LANCE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lancedb")

class SemanticMemory:
    """
    LanceDB backend for semantic search and RAG capabilities.
    Stores and retrieves high-dimensional vector embeddings of conversations,
    documents, and RAG contexts locally.
    """
    def __init__(self, gemini_api_key: str):
        os.makedirs(LANCE_DB_PATH, exist_ok=True)
        self.db = lancedb.connect(LANCE_DB_PATH)
        self.gemini_api_key = gemini_api_key
        
        # Initialize tables if they don't exist
        try:
            self.memory_table = self.db.open_table("semantic_memory")
        except FileNotFoundError:
            # Table doesn't exist yet, it will be created on first insertion
            self.memory_table = None

    async def _get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
        """Fetch embeddings from Gemini API directly using httpx."""
        if not self.gemini_api_key:
            logger.error("Missing Gemini API Key for semantic memory.")
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.gemini_api_key}"
        
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            },
            "taskType": task_type
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding", {}).get("values")
                else:
                    logger.error(f"Embedding failed: {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Embedding request failed: {e}")
                return None

    async def add_memory(self, text: str, metadata: Dict[str, Any]):
        """Add a chunk of text to semantic memory."""
        embedding = await self._get_embedding(text)
        if not embedding:
            return False

        record = [{"vector": embedding, "text": text, "metadata": str(metadata)}]
        
        if self.memory_table is None:
            self.memory_table = self.db.create_table("semantic_memory", data=record)
        else:
            self.memory_table.add(record)
        return True

    async def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search semantic memory for relevant chunks."""
        if self.memory_table is None:
            return []
            
        query_embedding = await self._get_embedding(query, "RETRIEVAL_QUERY")
        if not query_embedding:
            return []

        results = self.memory_table.search(query_embedding).limit(limit).to_list()
        return results

# Singleton instance initialized in ws_main
semantic_memory: Optional[SemanticMemory] = None
