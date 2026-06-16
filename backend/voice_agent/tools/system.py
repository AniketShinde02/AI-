import os
import subprocess
import logging
import psutil
from typing import Dict, Any, Optional

logger = logging.getLogger("nexus.tools.system")

# Security: Whitelist of safe base commands
SAFE_COMMANDS = {"dir", "ls", "echo", "type", "cat", "ipconfig", "systeminfo", "tasklist", "ping", "uptime"}
BLOCKED_KEYWORDS = {"rm", "del", "format", "mkfs", "shutdown", "reboot", "powershell", "kill"}

async def run_command(command: str) -> str:
    """
    Executes a shell command on the host machine.
    Includes security validation to prevent destructive operations.
    """
    base_cmd = command.split()[0].lower() if command.split() else ""
    
    # Simple safety check
    if any(keyword in command.lower() for keyword in BLOCKED_KEYWORDS):
        return f"Error: Command contains blocked keyword for safety."
    
    if base_cmd not in SAFE_COMMANDS:
        logger.warning(f"⚠️  Unrecognized command blocked: {command}")
        return f"Error: '{base_cmd}' is not in the allowed command whitelist."

    logger.info(f"🖥  Executing system command: {command}")
    try:
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        if process.returncode == 0:
            return f"Success:\n{process.stdout[:1000]}" # Truncate long output
        else:
            return f"Error (code {process.returncode}):\n{process.stderr[:500]}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 15 seconds."
    except Exception as e:
        return f"Error: {str(e)}"

async def open_application(app_name: str) -> str:
    """Opens a Windows application by name."""
    logger.info(f"🚀 Opening application: {app_name}")
    try:
        # Resolve common app names
        aliases = {
            "browser": "msedge",
            "chrome": "chrome",
            "edge": "msedge",
            "code": "code",
            "vscode": "code",
            "notepad": "notepad",
            "calculator": "calc",
            "calc": "calc",
            "explorer": "explorer",
            "terminal": "wt"
        }
        
        target_app = aliases.get(app_name.lower(), app_name)
        
        # Simple start command for Windows
        subprocess.Popen(f"start {target_app}", shell=True)
        return f"Successfully launched '{target_app}'."
    except Exception as e:
        return f"Failed to open '{app_name}': {str(e)}"

async def get_system_status() -> str:
    """Get the current system resource usage."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        status = [
            "🖥️ Nexus Host System Status:",
            f"- CPU Usage: {cpu}%",
            f"- RAM Usage: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)",
            f"- Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)",
            f"- Active Processes: {len(psutil.pids())}"
        ]
        return "\n".join(status)
    except Exception as e:
        return f"Failed to get system status: {str(e)}"

# Define the tool metadata for the LLM
SYSTEM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command on the local Windows machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to run."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a Windows application or file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the app (e.g. 'notepad', 'chrome', 'calc')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get current CPU, RAM, and Disk usage of the host machine.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
