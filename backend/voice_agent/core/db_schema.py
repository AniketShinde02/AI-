"""
db_schema.py
------------
Responsibility: All CREATE TABLE DDL + sync database initialisation.
Imported once by NexusDatabase.__init__() in database.py.

Do NOT put any async query methods here.
"""
import os
import sqlite3
import logging

logger = logging.getLogger("nexus.database")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nexus_core.db"
)


def init_db_sync(db_path: str = DB_PATH) -> None:
    """
    Run all CREATE TABLE IF NOT EXISTS statements synchronously at startup.
    Uses WAL journal mode for concurrent read performance.
    Safe to call multiple times (idempotent).
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT PRIMARY KEY,
                preferences JSON,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_matrix (
                feature TEXT PRIMARY KEY,
                status TEXT,
                last_test TIMESTAMP,
                result TEXT,
                evidence TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_apps (
                app_name TEXT PRIMARY KEY,
                executable_path TEXT,
                aliases JSON,
                publisher TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration guards — harmless if columns already exist
        for stmt in [
            "ALTER TABLE discovered_apps ADD COLUMN aliases JSON",
            "ALTER TABLE discovered_apps ADD COLUMN publisher TEXT",
        ]:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_state (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT,
                workspace_id TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id TEXT,
                capability_id TEXT,
                state TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, capability_id),
                FOREIGN KEY(capability_id) REFERENCES capabilities(id)
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace_settings (
                workspace_id TEXT PRIMARY KEY,
                preferences JSON,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            )
        """)

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

        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN workspace_id TEXT")
        except sqlite3.OperationalError:
            pass

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_identity (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed system identity variables
        identity_defaults = [
            ("owner", "Aniket"),
            ("project", "Nexus"),
            ("role", "Voice-First AI Operating System"),
            ("capabilities", "Desktop Control, Browser Automation, File Management, Personal Memory"),
            ("current_stage", "V1 Core Capabilities & Speech Corrections"),
            ("future_stage", "Brain V2 Planning")
        ]
        for k, v in identity_defaults:
            cursor.execute(
                "INSERT OR IGNORE INTO system_identity (key, value) VALUES (?, ?)",
                (k, v)
            )

        # Seed default user and workspace
        cursor.execute(
            "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
            ("default_user", "Aniket")
        )
        cursor.execute(
            "INSERT OR IGNORE INTO workspaces (id, user_id, name) VALUES (?, ?, ?)",
            ("default_workspace", "default_user", "Nexus")
        )
        conn.commit()
