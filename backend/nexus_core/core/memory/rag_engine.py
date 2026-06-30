import os
import logging
import httpx
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nexus.rag")

class RAGOracle:
    def __init__(self, gemini_api_key: str, groq_api_key: str):
        self.gemini_key = gemini_api_key
        self.groq_key = groq_api_key
        self.vector_db = []
        self.processed_files = set()
        self.current_workspace = None

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        a = np.array(vec_a)
        b = np.array(vec_b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    async def _get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
        """Fetch embeddings from Gemini API directly using httpx to avoid new dependencies."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.gemini_key}"
        
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

    async def ingest_codebase(self, dir_path: str) -> Dict[str, Any]:
        """Scan a directory, chunk text files, and embed them into LanceDB."""
        import asyncio
        from core.memory.vector_store import get_memory
        
        if not self.gemini_key:
            return {"success": False, "error": "GEMINI_API_KEY is missing."}
            
        target_path = os.path.normpath(dir_path)
        if not os.path.isdir(target_path):
            return {"success": False, "error": "Invalid directory path."}
            
        mem = await get_memory()
        
        from core.database import db
        import hashlib
        
        # We no longer load from .nexus_states JSON. We just rely on LanceDB.
        ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build', '.next'}
        allowed_exts = {'.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.json', '.txt'}
        
        all_files = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    all_files.append(os.path.join(root, file))
                    
        # Check if file hash changed in DB.
        files_to_process = []
        for fpath in all_files:
            try:
                with open(fpath, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                if not await db.get_ingestion_state(file_hash):
                    files_to_process.append((fpath, file_hash))
            except Exception:
                pass
                
        logger.info(f"Ingesting {len(files_to_process)} new/modified files into LanceDB...")
        
        chunks_added = 0
        for file_path, file_hash in files_to_process:
            try:
                # Skip huge files (>100KB, except markdown files which can be up to 1MB)
                max_size = 1_000_000 if file_path.endswith('.md') else 100_000
                if os.path.getsize(file_path) > max_size:
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                chunk_size = 1500
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                for idx, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 20: 
                        continue
                    
                    text_for_embed = f"File: {os.path.basename(file_path)}\n\n{chunk}"
                    
                    # Store in LanceDB
                    success = await mem.add_memory(
                        text=text_for_embed, 
                        metadata={"file_path": file_path, "type": "codebase"}
                    )
                    if success:
                        chunks_added += 1
                    
                    await asyncio.sleep(0.1) # Rate limiting
                    
                # Mark as processed in database
                await db.set_ingestion_state(file_hash, file_path)
                
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
                
        return {"success": True, "totalChunksAdded": chunks_added, "wasResumed": False}

    async def consult_oracle(self, query: str) -> Dict[str, Any]:
        """Query the vector database and generate an answer using Groq."""
        from core.memory.vector_store import get_memory
        
        if not self.gemini_key or not self.groq_key:
            return {"success": False, "answer": "Error: Missing API Keys."}
            
        mem = await get_memory()
        results = await mem.search_memory(query, limit=3)
        
        if not results:
            return {"success": False, "answer": "No relevant codebase context found. Please ingest the codebase first."}
        
        # Results from lancedb search contain 'vector', 'text', 'metadata', '_distance'
        context_text = ""
        scanned_files = []
        for r in results:
            text = r.get("text", "")
            # we injected metadata as string in lance_memory.py
            meta_str = r.get("metadata", "{}")
            try:
                import ast
                meta = ast.literal_eval(meta_str)
            except Exception:
                meta = {}
            fpath = meta.get("file_path", "Unknown File")
            scanned_files.append(fpath)
            context_text += f"\n\n// File: {fpath}\n{text}"
        
        # Consult Groq
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.groq_key)
            
            completion = await client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an elite coding assistant. Answer the user's question based ONLY on the provided codebase context. Give direct code snippets and explanations. Be concise."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context_text}\n\nQuestion: {query}"
                    }
                ],
                model="gpt-oss-20b"
            )
            
            answer = completion.choices[0].message.content
            return {
                "success": True,
                "answer": answer,
                "scannedFiles": scanned_files
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global singleton instance (to be initialized in ws_main.py)
oracle_instance: Optional[RAGOracle] = None
