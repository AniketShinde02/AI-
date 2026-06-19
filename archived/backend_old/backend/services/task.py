from ..core.firebase_db import FirebaseDB
from datetime import datetime
from typing import List, Dict, Any

class TaskService:
    def __init__(self):
        self.db = FirebaseDB.get_db()

    async def create_task(self, user_id: str, title: str, description: str = "", priority: str = "medium"):
        """Create a new task in Firestore."""
        task_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        return self.db.collection("tasks").add(task_data)

    async def get_user_tasks(self, user_id: str, status: str = None):
        """Fetch tasks for a specific user (Optimized for Free Tier)."""
        query = self.db.collection("tasks").where("user_id", "==", user_id)
        if status:
            query = query.where("status", "==", status)
        
        docs = query.order_by("created_at", direction="DESCENDING").stream()
        return [doc.to_dict() for doc in docs]

    async def batch_update_status(self, task_ids: List[str], status: str):
        """Update multiple tasks in one go using a Batch to save writes."""
        batch = self.db.batch()
        for t_id in task_ids:
            doc_ref = self.db.collection("tasks").document(t_id)
            batch.update(doc_ref, {"status": status, "updated_at": datetime.utcnow()})
        return batch.commit()

task_service = TaskService()
