"""
database.py
-----------
Responsibility: All async query methods for NexusDatabase.
Schema DDL is in db_schema.py and run once at startup via init_db_sync().
"""
import sqlite3
import aiosqlite
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from core.db_schema import DB_PATH, init_db_sync

logger = logging.getLogger("nexus.database")


class NexusDatabase:
    """
    Async SQLite query layer for Nexus.
    All reads/writes use aiosqlite to prevent GIL contention.
    Schema is initialised once synchronously at startup.
    """

    def __init__(self):
        init_db_sync()  # idempotent; runs DDL synchronously before the event loop starts

    # ------------------------------------------------------------------
    # Sync helper exposed for rest_routes.py capability/audit endpoints
    # (kept for backward-compat — only for read queries, not writes)
    # ------------------------------------------------------------------

    def _get_conn(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    # ------------------------------------------------------------------
    # Session / Message
    # ------------------------------------------------------------------

    async def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT role, content, metadata, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit)) as cursor:
                rows = await cursor.fetchall()
                history = [{
                    "role": row[0],
                    "content": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "timestamp": row[3]
                } for row in rows]
                return list(reversed(history))

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        workspace_id: str = "default_workspace"
    ):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO sessions (id, user_id, workspace_id, title) VALUES (?, ?, ?, ?)",
                (session_id, "default_user", workspace_id, "New Session")
            )
            await db.execute("""
                INSERT INTO messages (session_id, role, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, role, content,
                json.dumps(metadata) if metadata else None,
                datetime.now(timezone.utc).isoformat()
            ))
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), session_id)
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self, user_id: str = "default_user") -> Dict[str, Any]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT preferences FROM settings WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row and row[0] else {}

    async def update_settings(self, preferences: Dict[str, Any], user_id: str = "default_user"):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT preferences FROM settings WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                current_prefs = json.loads(row[0]) if row and row[0] else {}
                current_prefs.update(preferences)
            await db.execute("""
                INSERT INTO settings (user_id, preferences) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET preferences = excluded.preferences
            """, (user_id, json.dumps(current_prefs)))
            await db.commit()

    # ------------------------------------------------------------------
    # System Identity
    # ------------------------------------------------------------------

    async def get_system_identity(self) -> Dict[str, str]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT key, value FROM system_identity") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def update_system_identity(self, identity: Dict[str, str]):
        async with aiosqlite.connect(DB_PATH) as db:
            for k, v in identity.items():
                await db.execute("""
                    INSERT INTO system_identity (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (k, v))
            await db.commit()

    # ------------------------------------------------------------------
    # Sessions / Workspaces
    # ------------------------------------------------------------------

    async def get_recent_sessions(self, user_id: str = "default_user", limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT id, title, created_at, updated_at
                FROM sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [{"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]

    async def get_workspaces(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, created_at, updated_at FROM workspaces WHERE user_id = ?", (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"id": r[0], "name": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]

    async def create_workspace(self, workspace_id: str, name: str, user_id: str = "default_user"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO workspaces (id, user_id, name) VALUES (?, ?, ?)",
                (workspace_id, user_id, name)
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    async def get_notes(self, workspace_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, title, content, updated_at FROM notes WHERE workspace_id = ? ORDER BY updated_at DESC",
                (workspace_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"id": r[0], "title": r[1], "content": r[2], "updated_at": r[3]} for r in rows]

    async def save_note(self, workspace_id: str, title: str, content: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO notes (workspace_id, title, content) VALUES (?, ?, ?)",
                (workspace_id, title, content)
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    async def get_agents(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, status, description, color, runtime, calls FROM agents ORDER BY name ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "id": r[0], "name": r[1], "status": r[2],
                    "description": r[3], "color": r[4], "runtime": r[5], "calls": r[6]
                } for r in rows]

    async def create_agent(self, agent: Dict[str, Any]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO agents (id, name, status, description, color, runtime, calls)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agent["id"], agent["name"], agent.get("status", "idle"),
                agent.get("description", ""), agent.get("color", "#00FFFF"),
                agent.get("runtime", "0.0s"), agent.get("calls", 0)
            ))
            await db.commit()

    async def update_agent(self, agent_id: str, agent: Dict[str, Any]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE agents
                SET name=?, status=?, description=?, color=?, runtime=?, calls=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                agent["name"], agent["status"], agent["description"],
                agent["color"], agent["runtime"], agent["calls"], agent_id
            ))
            await db.commit()

    async def delete_agent(self, agent_id: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            await db.commit()

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    async def get_workflows(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, trigger, actions, status, runs, last_run FROM workflows ORDER BY name ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "id": r[0], "name": r[1], "trigger": r[2],
                    "actions": json.loads(r[3]), "status": r[4], "runs": r[5], "lastRun": r[6]
                } for r in rows]

    async def create_workflow(self, workflow: Dict[str, Any]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO workflows (id, name, trigger, actions, status, runs, last_run)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow["id"], workflow["name"], workflow["trigger"],
                json.dumps(workflow["actions"]), workflow.get("status", "draft"),
                workflow.get("runs", 0), workflow.get("lastRun", "Never")
            ))
            await db.commit()

    async def update_workflow(self, workflow_id: str, workflow: Dict[str, Any]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE workflows
                SET name=?, trigger=?, actions=?, status=?, runs=?, last_run=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                workflow["name"], workflow["trigger"], json.dumps(workflow["actions"]),
                workflow["status"], workflow["runs"], workflow["lastRun"], workflow_id
            ))
            await db.commit()

    async def delete_workflow(self, workflow_id: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
            await db.commit()

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    async def get_all_memory(self) -> Dict[str, Any]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT category, key, value FROM user_memory") as cursor:
                rows = await cursor.fetchall()
                mem: Dict[str, Any] = {}
                for category, key, value in rows:
                    if category not in mem:
                        mem[category] = {}
                    mem[category][key] = json.loads(value)
                return mem

    async def update_memory(self, category: str, key: str, value: Any):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO user_memory (category, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """, (category, key, json.dumps(value)))
            await db.commit()

    async def delete_memory(self, category: str, key: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM user_memory WHERE category=? AND key=?", (category, key))
            await db.commit()

    # ------------------------------------------------------------------
    # Capabilities & Permissions
    # ------------------------------------------------------------------

    async def register_capability(self, cap: Dict[str, Any]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO capabilities (id, name, description, category, permissions_required, requires_approval, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, description=excluded.description, category=excluded.category,
                    permissions_required=excluded.permissions_required,
                    requires_approval=excluded.requires_approval
            """, (
                cap["id"], cap["name"], cap["description"],
                cap.get("category", "System"),
                cap.get("permissions_required", False),
                cap.get("requires_approval", False),
                cap.get("enabled", True)
            ))
            await db.commit()

    async def get_capability(self, cap_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, description, category, permissions_required, requires_approval, enabled "
                "FROM capabilities WHERE id=?",
                (cap_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0], "name": row[1], "description": row[2],
                        "category": row[3], "permissions_required": bool(row[4]),
                        "requires_approval": bool(row[5]), "enabled": bool(row[6])
                    }
                return None

    async def get_user_permission(self, user_id: str, cap_id: str) -> Optional[str]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT state FROM user_permissions WHERE user_id=? AND capability_id=?",
                (user_id, cap_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_user_permission(self, user_id: str, cap_id: str, state: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO user_permissions (user_id, capability_id, state, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, capability_id) DO UPDATE SET
                    state=excluded.state, updated_at=CURRENT_TIMESTAMP
            """, (user_id, cap_id, state))
            await db.commit()

    async def log_tool_audit(
        self, tool_id: str, parameters_passed: Dict[str, Any],
        result_status: str, permission_state: str
    ):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO tool_audit_logs (tool_id, parameters_passed, result_status, permission_state)
                VALUES (?, ?, ?, ?)
            """, (tool_id, json.dumps(parameters_passed), result_status, permission_state))
            await db.commit()

    # ------------------------------------------------------------------
    # Verification matrix
    # ------------------------------------------------------------------

    async def log_verification(self, feature: str, status: str, result: str, evidence: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO verification_matrix (feature, status, last_test, result, evidence)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
                ON CONFLICT(feature) DO UPDATE SET
                    status=excluded.status, last_test=CURRENT_TIMESTAMP,
                    result=excluded.result, evidence=excluded.evidence
            """, (feature, status, result, evidence))
            await db.commit()

    async def get_verification_status(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT feature, status, last_test, result, evidence "
                "FROM verification_matrix ORDER BY feature ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "feature": r[0], "status": r[1], "last_test": r[2],
                    "result": r[3], "evidence": r[4]
                } for r in rows]

    # ------------------------------------------------------------------
    # Ingestion state
    # ------------------------------------------------------------------

    async def get_ingestion_state(self, file_hash: str) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM ingestion_state WHERE file_hash=?", (file_hash,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def set_ingestion_state(
        self, file_hash: str, file_path: str, workspace_id: Optional[str] = None
    ):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO ingestion_state (file_hash, file_path, workspace_id, processed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_hash) DO UPDATE SET
                    file_path=excluded.file_path,
                    workspace_id=excluded.workspace_id,
                    processed_at=CURRENT_TIMESTAMP
            """, (file_hash, file_path, workspace_id))
            await db.commit()

    # ------------------------------------------------------------------
    # Application discovery
    # ------------------------------------------------------------------

    async def get_all_applications(self) -> List[str]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT app_name, aliases FROM discovered_apps") as cursor:
                rows = await cursor.fetchall()
                apps = []
                for row in rows:
                    apps.append(row[0].lower())
                    try:
                        aliases = json.loads(row[1]) if row[1] else []
                        apps.extend([a.lower() for a in aliases])
                    except Exception:
                        pass
                return list(set(apps))


db = NexusDatabase()
