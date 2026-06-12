from ..core.firebase_db import FirebaseDB
from datetime import datetime
from functools import lru_cache

class ProfileService:
    def __init__(self):
        self.db = FirebaseDB.get_db()
        self._cache = {} # In-memory cache for the current session

    async def get_profile(self, user_id: str):
        """Get user profile with local caching to save Free Tier reads."""
        if user_id in self._cache:
            return self._cache[user_id]
            
        doc = self.db.collection("profiles").document(user_id).get()
        profile = doc.to_dict() if doc.exists else None
        
        if profile:
            self._cache[user_id] = profile
        return profile

    async def upsert_profile(self, user_id: str, email: str, metadata: dict = None):
        """Upsert user profile and clear local cache."""
        data = {
            "user_id": user_id,
            "email": email,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow()
        }
        if user_id in self._cache:
            del self._cache[user_id] # Invalidate cache on update
            
        return self.db.collection("profiles").document(user_id).set(data, merge=True)

profile_service = ProfileService()
