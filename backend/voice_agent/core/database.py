import sqlite3
import os
import json
import logging
import asyncio
from datetime import datetime
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
            cursor = conn.cursor()
            
            # Users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                """, (session_id, role, content, json.dumps(metadata) if metadata else None, datetime.utcnow().isoformat()))
                
                cursor.execute("""
                    UPDATE sessions SET updated_at = ? WHERE id = ?
                """, (datetime.utcnow().isoformat(), session_id))
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

db = NexusDatabase()
