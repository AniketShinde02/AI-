import sqlite3
import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nexus.database")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nexus_core.db")

class NexusDatabase:
    """
    SQLite backend for Nexus sessions, messages, users, and settings.
    Designed for fast local access.
    """
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        # Return a fresh connection per thread. SQLite handles concurrent reads, writes lock briefly.
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def _init_db(self):
        with self._get_conn() as conn:
            # Enable WAL mode for better concurrency and write performance
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            
            # Users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Agents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    status TEXT,
                    description TEXT,
                    color TEXT,
                    runtime TEXT,
                    calls INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Agent Runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    task TEXT,
                    result TEXT,
                    duration_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(agent_id) REFERENCES agents(id)
                )
            """)

            # User Memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    key TEXT,
                    value JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)

            # Agent Memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    key TEXT,
                    value JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(agent_id) REFERENCES agents(id)
                )
            """)

            # Workflows
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    trigger TEXT,
                    actions JSON,
                    status TEXT,
                    runs INTEGER DEFAULT 0,
                    last_run TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    user_id TEXT PRIMARY KEY,
                    preferences JSON,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # Workspaces
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # Capabilities (Tool Registry & Permissions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capabilities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    category TEXT,
                    permissions_required BOOLEAN,
                    requires_approval BOOLEAN,
                    enabled BOOLEAN DEFAULT 1
                )
            """)

            # Capability Verification Matrix
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verification_matrix (
                    feature TEXT PRIMARY KEY,
                    status TEXT,
                    last_test TIMESTAMP,
                    result TEXT,
                    evidence TEXT
                )
            """)

            # App Discovery
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovered_apps (
                    app_name TEXT PRIMARY KEY,
                    executable_path TEXT,
                    alias TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # File Ingestion State Tracker (Replaces JSON files in .nexus_states)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_state (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT,
                    workspace_id TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)


            # User Permissions for Capabilities
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    user_id TEXT,
                    capability_id TEXT,
                    state TEXT, -- 'Always Allow', 'Deny'
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, capability_id),
                    FOREIGN KEY(capability_id) REFERENCES capabilities(id)
                )
            """)

            # Tool Audit Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id TEXT,
                    parameters_passed JSON,
                    result_status TEXT,
                    permission_state TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Workspace Settings (Preferences per workspace)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workspace_settings (
                    workspace_id TEXT PRIMARY KEY,
                    preferences JSON,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                )
            """)

            # Sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    workspace_id TEXT,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                )
            """)
            
            # Migration for older DBs
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN workspace_id TEXT")
            except sqlite3.OperationalError:
                pass

            # Notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT,
                    title TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                )
            """)

            # Messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            
            # Seed default user and workspace if not exists
            cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", ("default_user", "Aniket"))
            cursor.execute("INSERT OR IGNORE INTO workspaces (id, user_id, name) VALUES (?, ?, ?)", ("default_workspace", "default_user", "Nexus"))
            conn.commit()

    async def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, metadata, timestamp 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (session_id, limit))
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        "role": row[0],
                        "content": row[1],
                        "metadata": json.loads(row[2]) if row[2] else {},
                        "timestamp": row[3]
                    })
                return list(reversed(history))
        
        return await asyncio.to_thread(_fetch)

    async def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None, workspace_id: str = "default_workspace"):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                # Ensure session exists (auto-create for now if missing)
                cursor.execute("INSERT OR IGNORE INTO sessions (id, user_id, workspace_id, title) VALUES (?, ?, ?, ?)", 
                               (session_id, "default_user", workspace_id, "New Session"))
                
                cursor.execute("""
                    INSERT INTO messages (session_id, role, content, metadata, timestamp) 
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, role, content, json.dumps(metadata) if metadata else None, datetime.now(timezone.utc).isoformat()))
                
                cursor.execute("""
                    UPDATE sessions SET updated_at = ? WHERE id = ?
                """, (datetime.now(timezone.utc).isoformat(), session_id))
                conn.commit()
                
        await asyncio.to_thread(_save)

    async def get_settings(self, user_id: str = "default_user") -> Dict[str, Any]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT preferences FROM settings WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return json.loads(row[0]) if row and row[0] else {}
        return await asyncio.to_thread(_fetch)

    async def update_settings(self, preferences: Dict[str, Any], user_id: str = "default_user"):
        def _update():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT preferences FROM settings WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                current_prefs = json.loads(row[0]) if row and row[0] else {}
                current_prefs.update(preferences)
                
                cursor.execute("""
                    INSERT INTO settings (user_id, preferences) VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET preferences = excluded.preferences
                """, (user_id, json.dumps(current_prefs)))
                conn.commit()
        await asyncio.to_thread(_update)

    async def get_recent_sessions(self, user_id: str = "default_user", limit: int = 20) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, created_at, updated_at 
                    FROM sessions 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                rows = cursor.fetchall()
                return [{"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]
        return await asyncio.to_thread(_fetch)

    async def get_workspaces(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, created_at, updated_at FROM workspaces WHERE user_id = ?", (user_id,))
                rows = cursor.fetchall()
                return [{"id": r[0], "name": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]
        return await asyncio.to_thread(_fetch)

    async def create_workspace(self, workspace_id: str, name: str, user_id: str = "default_user"):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO workspaces (id, user_id, name) VALUES (?, ?, ?)", (workspace_id, user_id, name))
                conn.commit()
        await asyncio.to_thread(_save)

    async def get_notes(self, workspace_id: str) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, content, updated_at FROM notes WHERE workspace_id = ? ORDER BY updated_at DESC", (workspace_id,))
                rows = cursor.fetchall()
                return [{"id": r[0], "title": r[1], "content": r[2], "updated_at": r[3]} for r in rows]
        return await asyncio.to_thread(_fetch)

    async def save_note(self, workspace_id: str, title: str, content: str):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO notes (workspace_id, title, content) VALUES (?, ?, ?)", (workspace_id, title, content))
                conn.commit()
        await asyncio.to_thread(_save)

    # --- AGENT METHODS ---
    async def get_agents(self) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, status, description, color, runtime, calls FROM agents ORDER BY name ASC")
                rows = cursor.fetchall()
                return [{"id": r[0], "name": r[1], "status": r[2], "description": r[3], "color": r[4], "runtime": r[5], "calls": r[6]} for r in rows]
        return await asyncio.to_thread(_fetch)

    async def create_agent(self, agent: Dict[str, Any]):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO agents (id, name, status, description, color, runtime, calls) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (agent["id"], agent["name"], agent.get("status", "idle"), agent.get("description", ""), agent.get("color", "#00FFFF"), agent.get("runtime", "0.0s"), agent.get("calls", 0)))
                conn.commit()
        await asyncio.to_thread(_save)

    async def update_agent(self, agent_id: str, agent: Dict[str, Any]):
        def _update():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agents 
                    SET name = ?, status = ?, description = ?, color = ?, runtime = ?, calls = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (agent["name"], agent["status"], agent["description"], agent["color"], agent["runtime"], agent["calls"], agent_id))
                conn.commit()
        await asyncio.to_thread(_update)

    async def delete_agent(self, agent_id: str):
        def _delete():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
                conn.commit()
        await asyncio.to_thread(_delete)

    # --- WORKFLOW METHODS ---
    async def get_workflows(self) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, trigger, actions, status, runs, last_run FROM workflows ORDER BY name ASC")
                rows = cursor.fetchall()
                return [{"id": r[0], "name": r[1], "trigger": r[2], "actions": json.loads(r[3]), "status": r[4], "runs": r[5], "lastRun": r[6]} for r in rows]
        return await asyncio.to_thread(_fetch)

    async def create_workflow(self, workflow: Dict[str, Any]):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO workflows (id, name, trigger, actions, status, runs, last_run) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (workflow["id"], workflow["name"], workflow["trigger"], json.dumps(workflow["actions"]), workflow.get("status", "draft"), workflow.get("runs", 0), workflow.get("lastRun", "Never")))
                conn.commit()
        await asyncio.to_thread(_save)

    async def update_workflow(self, workflow_id: str, workflow: Dict[str, Any]):
        def _update():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE workflows 
                    SET name = ?, trigger = ?, actions = ?, status = ?, runs = ?, last_run = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (workflow["name"], workflow["trigger"], json.dumps(workflow["actions"]), workflow["status"], workflow["runs"], workflow["lastRun"], workflow_id))
                conn.commit()
        await asyncio.to_thread(_update)

    async def delete_workflow(self, workflow_id: str):
        def _delete():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                conn.commit()
        await asyncio.to_thread(_delete)

    # --- USER MEMORY METHODS ---
    async def get_all_memory(self) -> Dict[str, Any]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT category, key, value FROM user_memory")
                rows = cursor.fetchall()
                mem = {}
                for category, key, value in rows:
                    if category not in mem:
                        mem[category] = {}
                    mem[category][key] = json.loads(value)
                return mem
        return await asyncio.to_thread(_fetch)

    async def update_memory(self, category: str, key: str, value: Any):
        def _update():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_memory (category, key, value) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(category, key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """, (category, key, json.dumps(value)))
                conn.commit()
        await asyncio.to_thread(_update)

    async def delete_memory(self, category: str, key: str):
        def _delete():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_memory WHERE category = ? AND key = ?", (category, key))
                conn.commit()
        await asyncio.to_thread(_delete)

    # --- CAPABILITIES & PERMISSIONS ---
    async def register_capability(self, cap: Dict[str, Any]):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO capabilities (id, name, description, category, permissions_required, requires_approval, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, description=excluded.description, category=excluded.category,
                    permissions_required=excluded.permissions_required, requires_approval=excluded.requires_approval
                """, (cap['id'], cap['name'], cap['description'], cap.get('category', 'System'), cap.get('permissions_required', False), cap.get('requires_approval', False), cap.get('enabled', True)))
                conn.commit()
        await asyncio.to_thread(_save)

    async def get_capability(self, cap_id: str) -> Optional[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description, category, permissions_required, requires_approval, enabled FROM capabilities WHERE id=?", (cap_id,))
                row = cursor.fetchone()
                if row:
                    return {"id": row[0], "name": row[1], "description": row[2], "category": row[3], "permissions_required": bool(row[4]), "requires_approval": bool(row[5]), "enabled": bool(row[6])}
                return None
        return await asyncio.to_thread(_fetch)

    async def get_user_permission(self, user_id: str, cap_id: str) -> Optional[str]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT state FROM user_permissions WHERE user_id=? AND capability_id=?", (user_id, cap_id))
                row = cursor.fetchone()
                return row[0] if row else None
        return await asyncio.to_thread(_fetch)

    async def set_user_permission(self, user_id: str, cap_id: str, state: str):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_permissions (user_id, capability_id, state, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, capability_id) DO UPDATE SET state=excluded.state, updated_at=CURRENT_TIMESTAMP
                """, (user_id, cap_id, state))
                conn.commit()
        await asyncio.to_thread(_save)

    async def log_tool_audit(self, tool_id: str, parameters_passed: Dict[str, Any], result_status: str, permission_state: str):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tool_audit_logs (tool_id, parameters_passed, result_status, permission_state)
                    VALUES (?, ?, ?, ?)
                """, (tool_id, json.dumps(parameters_passed), result_status, permission_state))
                conn.commit()
        await asyncio.to_thread(_save)

    # --- VERIFICATION MATRIX (Rule 8) ---
    async def log_verification(self, feature: str, status: str, result: str, evidence: str):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO verification_matrix (feature, status, last_test, result, evidence)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
                    ON CONFLICT(feature) DO UPDATE SET 
                        status=excluded.status, 
                        last_test=CURRENT_TIMESTAMP, 
                        result=excluded.result, 
                        evidence=excluded.evidence
                """, (feature, status, result, evidence))
                conn.commit()
        await asyncio.to_thread(_save)

    async def get_verification_status(self) -> List[Dict[str, Any]]:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT feature, status, last_test, result, evidence FROM verification_matrix ORDER BY feature ASC")
                rows = cursor.fetchall()
                return [{"feature": r[0], "status": r[1], "last_test": r[2], "result": r[3], "evidence": r[4]} for r in rows]
        return await asyncio.to_thread(_fetch)

    # --- INGESTION STATE (File Parsing tracking) ---
    async def get_ingestion_state(self, file_hash: str) -> bool:
        def _fetch():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM ingestion_state WHERE file_hash=?", (file_hash,))
                return cursor.fetchone() is not None
        return await asyncio.to_thread(_fetch)

    async def set_ingestion_state(self, file_hash: str, file_path: str, workspace_id: Optional[str] = None):
        def _save():
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ingestion_state (file_hash, file_path, workspace_id, processed_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(file_hash) DO UPDATE SET 
                        file_path=excluded.file_path, 
                        workspace_id=excluded.workspace_id,
                        processed_at=CURRENT_TIMESTAMP
                """, (file_hash, file_path, workspace_id))
                conn.commit()
        await asyncio.to_thread(_save)

db = NexusDatabase()
