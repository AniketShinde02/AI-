from ..core.firebase_db import FirebaseDB
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

class MemoryService:
    def __init__(self):
        logger.debug("Initializing MemoryService...")
        self._db = None

    @property
    def db(self):
        if self._db is None:
            try:
                self._db = FirebaseDB.get_db()
            except Exception as e:
                logger.warning(f"⚠️ MemoryService: Firestore not available: {e}")
        return self._db


    async def save_interaction(self, user_id: str, role: str, content: str, metadata: dict = None):
        """Save a voice interaction to Firestore."""
        if not self.db:
            logger.warning("skipping save_interaction: Firestore not available.")
            return
        
        logger.debug(f"💾 Saving interaction for {user_id} | Role: {role}")
        try:
            interaction = {
                "user_id": user_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow()
            }
            self.db.collection("memories").add(interaction)
            logger.debug(f"✅ Interaction saved to Firestore.")
        except Exception as e:
            logger.error(f"❌ Failed to save interaction: {e}")

    async def get_recent_context(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent context from Firestore."""
        if not self.db:
            logger.warning("skipping get_recent_context: Firestore not available.")
            return []
            
        logger.debug(f"🔍 Retrieving last {limit} messages for user {user_id}")
        try:
            docs = self.db.collection("memories")\
                .where("user_id", "==", user_id)\
                .order_by("timestamp", direction="DESCENDING")\
                .limit(limit).stream()
            
            results = [doc.to_dict() for doc in docs]
            logger.debug(f"✅ Retrieved {len(results)} messages from Firestore.")
            return results
        except Exception as e:
            logger.error(f"❌ Failed to retrieve context: {e}")
            return []

    async def save_task(self, user_id: str, task_data: dict):
        """Save a task to the user's tasks collection."""
        if not self.db: return
        try:
            task_data["user_id"] = user_id
            task_data["created_at"] = datetime.utcnow()
            task_data["status"] = task_data.get("status", "pending")
            self.db.collection("tasks").add(task_data)
            logger.info(f"📌 Task saved for {user_id}: {task_data.get('title')}")
        except Exception as e:
            logger.error(f"❌ Failed to save task: {e}")

    async def save_note(self, user_id: str, note_data: dict):
        """Save a note to the user's notes collection."""
        if not self.db: return
        try:
            note_data["user_id"] = user_id
            note_data["created_at"] = datetime.utcnow()
            self.db.collection("notes").add(note_data)
            logger.info(f"🗒️ Note saved for {user_id}: {note_data.get('title')}")
        except Exception as e:
            logger.error(f"❌ Failed to save note: {e}")

memory_service = MemoryService()

