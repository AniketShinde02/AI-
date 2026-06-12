import os
import json
import logging
import httpx
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nexus.rag")

class RAGOracle:
    def __init__(self, gemini_api_key: str, groq_api_key: str):
        self.gemini_key = gemini_api_key
        self.groq_key = groq_api_key
        self.vector_db = []
        self.processed_files = set()
        
        # Load state if it exists (for a specific workspace)
        self.state_dir = Path.home() / ".nexus_states"
        self.state_dir.mkdir(exist_ok=True)
        self.current_workspace = None

    def _get_state_path(self, dir_path: str) -> Path:
        import hashlib
        h = hashlib.md5(os.path.normpath(dir_path).encode()).hexdigest()
        return self.state_dir / f"{h}.json"

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
        """Scan a directory, chunk text files, and embed them."""
        import asyncio
        
        if not self.gemini_key:
            return {"success": False, "error": "GEMINI_API_KEY is missing."}
            
        target_path = os.path.normpath(dir_path)
        if not os.path.isdir(target_path):
            return {"success": False, "error": "Invalid directory path."}
            
        state_file = self._get_state_path(target_path)
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.vector_db = state.get("vectorDB", [])
                    self.processed_files = set(state.get("processedFiles", []))
                    logger.info(f"Loaded existing RAG state with {len(self.vector_db)} chunks.")
                    return {"success": True, "totalChunks": len(self.vector_db), "wasResumed": True}
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                
        self.vector_db = []
        self.processed_files = set()
        
        ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build', '.next'}
        allowed_exts = {'.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.json', '.txt'}
        
        all_files = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    all_files.append(os.path.join(root, file))
                    
        files_to_process = [f for f in all_files if f not in self.processed_files]
        logger.info(f"Found {len(files_to_process)} new files to ingest out of {len(all_files)} total.")
        
        for file_path in files_to_process:
            try:
                if os.path.getsize(file_path) > 100_000: # Skip huge files
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Simple chunking by character length (roughly 1500 chars)
                chunk_size = 1500
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                for idx, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 20: continue
                    
                    text_for_embed = f"File: {os.path.basename(file_path)}\n\n{chunk}"
                    embedding = await self._get_embedding(text_for_embed, "RETRIEVAL_DOCUMENT")
                    
                    if embedding:
                        self.vector_db.append({
                            "filePath": file_path,
                            "chunk": chunk,
                            "embedding": embedding
                        })
                    await asyncio.sleep(0.5) # Rate limiting
                
                self.processed_files.add(file_path)
                
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
                
        # Save state
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "dirPath": target_path,
                    "processedFiles": list(self.processed_files),
                    "vectorDB": self.vector_db
                }, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            
        return {"success": True, "totalChunks": len(self.vector_db), "wasResumed": False}

    async def consult_oracle(self, query: str) -> Dict[str, Any]:
        """Query the vector database and generate an answer using Groq."""
        if not self.vector_db:
            return {"success": False, "answer": "Error: No files loaded into memory. Please run ingest_codebase first."}
            
        if not self.gemini_key or not self.groq_key:
            return {"success": False, "answer": "Error: Missing API Keys."}
            
        query_embedding = await self._get_embedding(query, "RETRIEVAL_QUERY")
        if not query_embedding:
            return {"success": False, "answer": "Error: Failed to generate embedding for query."}
            
        # Rank chunks
        for item in self.vector_db:
            item["score"] = self._cosine_similarity(query_embedding, item["embedding"])
            
        ranked = sorted(self.vector_db, key=lambda x: x["score"], reverse=True)[:3]
        
        context_text = "\n\n".join([f"// File: {c['filePath']}\n{c['chunk']}" for c in ranked])
        
        # Consult Groq
        from providers.llm import GroqLLM
        try:
            # We use the official groq SDK directly for a simple completion
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
                model="llama-3.1-8b-instant"
            )
            
            answer = completion.choices[0].message.content
            return {
                "success": True,
                "answer": answer,
                "scannedFiles": [c["filePath"] for c in ranked]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global singleton instance (to be initialized in ws_main.py)
oracle_instance: Optional[RAGOracle] = None
