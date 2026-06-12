import os
import subprocess
import logging
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
        # Simple start command for Windows
        subprocess.Popen(f"start {app_name}", shell=True)
        return f"Attempting to open {app_name}..."
    except Exception as e:
        return f"Failed to open {app_name}: {str(e)}"

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
    }
]
