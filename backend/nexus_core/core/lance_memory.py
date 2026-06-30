import os
import logging
from typing import List, Dict, Any, Optional
import httpx
import hashlib
import time

logger = logging.getLogger("nexus.lance_memory")

LANCE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lancedb")

import asyncio

class SemanticMemory:
    """
    LanceDB backend for semantic search and RAG capabilities.
    Stores and retrieves high-dimensional vector embeddings of conversations,
    documents, and RAG contexts locally.
    """
    def __init__(self, gemini_api_key: str):
        os.makedirs(LANCE_DB_PATH, exist_ok=True)
        self.db = None
        self.gemini_api_key = gemini_api_key
        self.memory_table = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Asynchronously initialize the LanceDB connection on demand."""
        if self._initialized: return
        
        import lancedb
        self.db = await lancedb.connect_async(LANCE_DB_PATH)
        try:
            self.memory_table = await self.db.open_table("semantic_memory")
        except (FileNotFoundError, ValueError):
            self.memory_table = None
            
        self._initialized = True

    async def initialize(self):
        # Legacy stub for ws_main.py so it doesn't crash if called
        pass

    async def _get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 3) -> Optional[List[float]]:
        """Fetch embeddings from Gemini API directly using httpx with async exponential backoff."""
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
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("embedding", {}).get("values")
                    elif response.status_code == 429 or response.status_code >= 500:
                        wait_time = 2 ** attempt
                        logger.warning(f"Embedding rate limited or server error ({response.status_code}). Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Embedding failed: {response.text}")
                        return None
                except (httpx.ReadTimeout, httpx.ConnectError) as e:
                    wait_time = 2 ** attempt
                    logger.warning(f"Embedding request network issue ({type(e).__name__}). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    logger.error(f"Embedding request failed: {e}")
                    return None
            logger.error("Max retries exceeded for embedding request.")
            return None

    async def add_memory(self, text: str, metadata: Dict[str, Any], source: str = "system"):
        """Add a chunk of text to semantic memory with deduplication."""
        await self._ensure_initialized()
        if not self.db:
            return False
            
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        
        if self.memory_table is not None:
            # Prevent duplicate memories from polluting LanceDB
            existing = await self.memory_table.search().where(f"content_hash = '{content_hash}'").limit(1).to_list()
            if existing:
                logger.debug("Memory already exists in LanceDB. Skipping duplicate.")
                return True
            
        embedding = await self._get_embedding(text)
        if not embedding:
            return False

        record = [{
            "vector": embedding,
            "text": text,
            "metadata": str(metadata),
            "content_hash": content_hash,
            "source": source,
            "timestamp": int(time.time())
        }]
        
        if self.memory_table is None:
            self.memory_table = await self.db.create_table("semantic_memory", data=record)
        else:
            await self.memory_table.add(record)
            
        return True

    async def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search semantic memory for relevant chunks."""
        await self._ensure_initialized()
        if self.memory_table is None:
            return []
            
        query_embedding = await self._get_embedding(query, "RETRIEVAL_QUERY")
        if not query_embedding:
            return []

        q = await self.memory_table.search(query_embedding)
        results = await q.limit(limit).to_list()
        
        return results

# Singleton instance initialized lazily
semantic_memory: Optional[SemanticMemory] = None

async def get_memory() -> SemanticMemory:
    global semantic_memory
    if semantic_memory is None:
        semantic_memory = SemanticMemory(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "")
        )
        await semantic_memory._ensure_initialized()
    return semantic_memory
