import os
import time
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# We'll try to use the Firebase implementation if available, 
# otherwise fall back to a local/memory store for development
try:
    from firebase_admin import firestore
    import firebase_admin
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False

logger = logging.getLogger("nexus.memory")

class MemoryEngine:
    """
    Handles persistent conversation context and user memory.
    Optimized for voice latency.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._db = None
        if HAS_FIREBASE:
            try:
                # Initialize Firebase if not already
                if not firebase_admin._apps:
                    creds_env = os.environ.get("FIREBASE_CREDENTIALS")
                    import json
                    from firebase_admin import credentials
                    
                    cred = None
                    
                    if creds_env:
                        creds_env = creds_env.strip()
                        # 1. Strip potential surrounding quotes (common in .env files)
                        if (creds_env.startswith("'") and creds_env.endswith("'")) or \
                           (creds_env.startswith('"') and creds_env.endswith('"')):
                            creds_env = creds_env[1:-1].strip()
                        
                        # 2. Try parsing from ENV as JSON string
                        if creds_env.startswith("{"):
                            try:
                                raw_json = creds_env
                                try:
                                    cred_dict = json.loads(raw_json)
                                except json.JSONDecodeError as je:
                                    # Sanitization attempt: fix common .env literal backslash issues
                                    logger.warning(f"Initial JSON parse failed: {je}. Attempting sanitization...")
                                    # Case 1: \n was meant to be a newline but became a literal backslash + n
                                    # In JSON, \n inside a string is valid. But if the string itself has literal backslashes
                                    # that are NOT escapes, json.loads fails.
                                    # Let's try to fix literal newlines first
                                    sanitized = raw_json.replace('\n', '\\n').replace('\r', '\\r')
                                    try:
                                        cred_dict = json.loads(sanitized)
                                    except:
                                        logger.error(f"Failed to parse FIREBASE_CREDENTIALS. Index of error: {je.pos}")
                                        logger.error(f"Context: {raw_json[max(0, je.pos-20):je.pos+20]}")
                                        raise je

                                # CRITICAL: Ensure private_key has actual newlines for PEM decoding
                                if "private_key" in cred_dict:
                                    pk = cred_dict["private_key"]
                                    # Replace literal "\n" (2 chars) with real newline (1 char)
                                    cred_dict["private_key"] = pk.replace("\\n", "\n")
                                    
                                cred = credentials.Certificate(cred_dict)
                                logger.info("🔑 Initialized Firebase from ENV JSON string.")
                            except Exception as e:
                                logger.error(f"❌ Failed to parse FIREBASE_CREDENTIALS JSON: {e}")
                                # If it looked like JSON but failed, we might want to fail fast or try file fallback
                    
                    # 2. Try file-based credentials if ENV was a path or JSON failed
                    if not cred:
                        import glob
                        
                        # Use path from ENV if it's not JSON, otherwise check defaults
                        potential_path = creds_env if creds_env and not creds_env.strip().startswith("{") else None
                        
                        # Search patterns for service account keys
                        # Look in current dir, parent (backend/), and common names
                        search_patterns = [
                            potential_path,
                            "firebase-key.json",
                            "../firebase-key.json",
                            "*firebase-adminsdk*.json",
                            "../*firebase-adminsdk*.json"
                        ]
                        
                        for pattern in search_patterns:
                            if not pattern: continue
                            
                            # Handle glob patterns
                            matches = glob.glob(pattern) if "*" in pattern else [pattern]
                            for path in matches:
                                if os.path.exists(path):
                                    try:
                                        cred = credentials.Certificate(path)
                                        logger.info(f"🔑 Initialized Firebase from file: {path}")
                                        break
                                    except Exception as e:
                                        logger.warning(f"⚠️ Failed to load key from {path}: {e}")
                            if cred: break

                    # 3. Fallback to ADC or initialize
                    if cred:
                        firebase_admin.initialize_app(cred)
                    else:
                        logger.info("🔑 Initialized Firebase using Application Default Credentials (ADC).")
                        firebase_admin.initialize_app()

                self._db = firestore.client()
                logger.info("✅ Firestore client connected successfully.")
            except Exception as e:
                logger.error(f"❌ MemoryEngine: Firebase/Firestore initialization failed: {e}")
                # We don't raise here to allow the agent to start in 'local mode' if needed,
                # though most features will fail.
        
        self._local_history: List[Dict[str, Any]] = []

    async def save_interaction(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Saves an interaction to the persistent store."""
        timestamp = datetime.utcnow()
        interaction = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": timestamp
        }
        
        # 1. Update local cache
        self._local_history.append(interaction)
        if len(self._local_history) > 20:
            self._local_history.pop(0)

        # 2. Async save to Firestore
        if self._db:
            try:
                # Firestore sync calls block the event loop, so we run in a thread
                asyncio.create_task(
                    asyncio.to_thread(
                        self._db.collection("users").document(self.user_id).collection("voice_history").add,
                        interaction
                    )
                )
            except Exception as e:
                logger.error(f"❌ MemoryEngine: Failed to save to Firestore: {e}")

    async def get_recent_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent messages to provide context to the LLM."""
        if not self._db:
            return self._local_history[-limit:]

        try:
            # Query Firestore for recent messages
            docs = self._db.collection("users").document(self.user_id)\
                .collection("voice_history")\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                .limit(limit).stream()
            
            history = []
            for doc in docs:
                data = doc.to_dict()
                history.append({
                    "role": data.get("role"),
                    "content": data.get("content")
                })
            
            # Firestore gives newest first, reverse for LLM context
            return list(reversed(history))
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to fetch context: {e}")
            return self._local_history[-limit:]

    async def update_profile(self, preferences: Dict[str, Any]):
        """Merge new preferences into the user's persistent profile."""
        if not self._db:
            logger.info(f"📝 Local Profile Update (No DB): {preferences}")
            return

        try:
            # Merge logic for Firestore
            asyncio.create_task(
                asyncio.to_thread(
                    self._db.collection("users").document(self.user_id).set,
                    preferences,
                    merge=True
                )
            )
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to update profile: {e}")

    async def get_user_profile(self) -> Dict[str, Any]:
        """Fetch user preferences, name, and persistent 'facts'."""
        if not self._db:
            return {"name": "Aniket", "preferences": {}}
            
        try:
            doc = self._db.collection("users").document(self.user_id).get()
            if doc.exists:
                return doc.to_dict()
            return {"name": "Aniket", "preferences": {}}
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to fetch profile: {e}")
            return {"name": "Aniket", "preferences": {}}
    async def save_task(self, task: Dict[str, Any]):
        """Saves a task to the user's tasks collection."""
        if not self._db:
            logger.info(f"📌 Local Task (No DB): {task}")
            return

        task["timestamp"] = datetime.utcnow()
        task["status"] = task.get("status", "pending")
        
        try:
            asyncio.create_task(
                asyncio.to_thread(
                    self._db.collection("users").document(self.user_id).collection("tasks").add,
                    task
                )
            )
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to save task: {e}")

    async def save_note(self, note: Dict[str, Any]):
        """Saves a note to the user's notes collection."""
        if not self._db:
            logger.info(f"🗒️ Local Note (No DB): {note}")
            return

        note["timestamp"] = datetime.utcnow()
        
        try:
            asyncio.create_task(
                asyncio.to_thread(
                    self._db.collection("users").document(self.user_id).collection("notes").add,
                    note
                )
            )
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to save note: {e}")
