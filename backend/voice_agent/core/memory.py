import os
import time
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from .database import db

logger = logging.getLogger("nexus.memory")

class MemoryEngine:
    """
    Handles persistent conversation context and user memory using SQLite.
    Optimized for fast local desktop access.
    """
    def __init__(self, user_id: str, session_id: str = "default_session"):
        self.user_id = user_id
        self.session_id = session_id
        self._local_history: List[Dict[str, Any]] = []

    async def initialize(self):
        """Loads recent context from SQLite into hot RAM."""
        try:
            history = await db.get_session_history(self.session_id, limit=20)
            self._local_history = history
            logger.info(f"✅ MemoryEngine: Loaded {len(history)} messages for session {self.session_id}")
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to load history: {e}")

    async def save_interaction(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Saves an interaction to the persistent store."""
        timestamp = datetime.utcnow().isoformat()
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

        # 2. Async save to SQLite
        try:
            await db.save_message(self.session_id, role, content, metadata)
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to save to SQLite: {e}")

    async def get_recent_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent messages to provide context to the LLM."""
        # For ultra-low latency TTS response, we return hot RAM cache
        # SQLite is fast enough to query directly, but RAM is instantaneous.
        return self._local_history[-limit:]

    async def update_profile(self, preferences: Dict[str, Any]):
        """Merge new preferences into the user's persistent profile."""
        try:
            await db.update_settings(preferences, self.user_id)
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to update profile: {e}")

    async def get_user_profile(self) -> Dict[str, Any]:
        """Fetch user preferences, name, and persistent 'facts'."""
        try:
            prefs = await db.get_settings(self.user_id)
            return {"name": "Aniket", "preferences": prefs}
        except Exception as e:
            logger.error(f"❌ MemoryEngine: Failed to fetch profile: {e}")
            return {"name": "Aniket", "preferences": {}}

    async def save_task(self, task: Dict[str, Any]):
        """Placeholder for tasks (Will go to SQLite task table later)"""
        logger.info(f"📌 Task saved (placeholder): {task}")

    async def save_note(self, note: Dict[str, Any]):
        """Placeholder for notes (Will go to SQLite notes table later)"""
        logger.info(f"🗒️ Note saved (placeholder): {note}")
