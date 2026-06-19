import asyncio
import json
import logging
import subprocess
from core.database import db
from typing import Optional

logger = logging.getLogger("nexus.app_discovery")

async def run_discovery():
    """
    Run App Discovery via PowerShell Get-StartApps to find installed apps.
    Satisfies Rule 3 (Auto Discovery) and Rule 10 (EXE Thinking).
    """
    logger.info("🔍 Running background app discovery...")
    
    def _fetch_apps():
        discovered = []
        try:
            # We use powershell to get Start Menu apps
            cmd = ["powershell.exe", "-Command", "Get-StartApps | ConvertTo-Json -Compress"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                discovered.extend(json.loads(result.stdout))
        except Exception as e:
            logger.error(f"Failed to run Get-StartApps: {e}")

        # Dynamic Crawler for .lnk files
        import os
        import glob
        try:
            scan_paths = [
                os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs"),
                os.path.join(os.environ.get("AppData", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
            ]
            for base_path in scan_paths:
                if not os.path.exists(base_path):
                    continue
                for path in glob.glob(f"{base_path}/**/*.lnk", recursive=True):
                    app_name = os.path.splitext(os.path.basename(path))[0]
                    
                    # Ignore uninstaller and documentation shortcuts
                    lower_name = app_name.lower()
                    if any(kw in lower_name for kw in ["uninstall", "help", "documentation", "readme", "setup"]):
                        continue
                        
                    # We store the absolute path instead of an AppID
                    discovered.append({
                        "Name": app_name,
                        "AppID": path,
                        "IsShortcut": True
                    })
        except Exception as e:
            logger.error(f"Failed to scan .lnk files: {e}")
            
        return discovered

    apps = await asyncio.to_thread(_fetch_apps)
    
    if not apps:
        logger.warning("No apps discovered.")
        return

    # apps is a list of dicts: {"Name": "Google Chrome", "AppID": "..."}
    # For regular exe paths we might need WMI or registry, but StartApps AppID can be launched via shell:AppsFolder\AppID
    
    def _get_default_aliases(name: str) -> list[str]:
        name_lower = name.lower()
        aliases = [name_lower]
        if "visual studio code" in name_lower:
            aliases.extend(["vs code", "vscode", "code"])
        elif "google chrome" in name_lower:
            aliases.extend(["chrome", "chrome browser"])
        elif "microsoft edge" in name_lower:
            aliases.extend(["edge"])
        elif "cursor" in name_lower:
            aliases.extend(["cursor ai", "cursor editor"])
        return list(set(aliases))

    def _save_apps(discovered):
        with db._get_conn() as conn:
            cursor = conn.cursor()
            for app in discovered:
                name = app.get("Name", "")
                app_id = app.get("AppID", "")
                if not name or not app_id:
                    continue
                
                aliases = _get_default_aliases(name)
                
                # Check if it's an absolute shortcut path
                if app.get("IsShortcut"):
                    executable_path = app_id
                else:
                    # AppID is what we pass to 'start shell:AppsFolder\AppID'
                    executable_path = f"shell:AppsFolder\\{app_id}"
                
                try:
                    cursor.execute("""
                        INSERT INTO discovered_apps (app_name, executable_path, aliases, publisher)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(app_name) DO UPDATE SET 
                            executable_path=excluded.executable_path, 
                            aliases=excluded.aliases
                    """, (name, executable_path, json.dumps(aliases), ""))
                except sqlite3.OperationalError:
                    # Fallback for old schema without JSON aliases if migration hasn't completed
                    pass
            conn.commit()

    await asyncio.to_thread(_save_apps, apps)
    logger.info(f"✅ Discovered and saved {len(apps)} applications to DB.")

async def get_app_path(app_alias: str) -> Optional[str]:
    """Find an app path by its exact name or substring."""
    def _fetch():
        with db._get_conn() as conn:
            cursor = conn.cursor()
            query = f"%{app_alias.lower()}%"
            # Since aliases might be JSON now, we check app_name instead as a fallback
            cursor.execute("SELECT executable_path FROM discovered_apps WHERE app_name LIKE ? LIMIT 1", (query,))
            row = cursor.fetchone()
            return row[0] if row else None
    return await asyncio.to_thread(_fetch)

async def get_all_apps() -> list[str]:
    """Return a list of all discovered application names."""
    def _fetch():
        with db._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT app_name FROM discovered_apps")
            rows = cursor.fetchall()
            return [row[0] for row in rows] if rows else []
    return await asyncio.to_thread(_fetch)

async def get_all_apps_dict() -> dict:
    """Return a dictionary of {alias: executable_path} for exact/fuzzy matching."""
    def _fetch():
        with db._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT app_name, aliases, executable_path FROM discovered_apps")
                rows = cursor.fetchall()
                result = {}
                for app_name, aliases_json, executable_path in rows:
                    if aliases_json:
                        try:
                            aliases = json.loads(aliases_json)
                            for alias in aliases:
                                result[alias.lower()] = executable_path
                        except:
                            result[app_name.lower()] = executable_path
                    else:
                        result[app_name.lower()] = executable_path
                return result
            except sqlite3.OperationalError:
                return {}
    return await asyncio.to_thread(_fetch)
