import os
import subprocess
import logging
import json
from typing import Dict, Any, List, Optional
from duckduckgo_search import DDGS
from ...services.memory import memory_service

from ..providers import nexus_log

logger = logging.getLogger("nexus.voice.tools")

# --- System Tools ---
SAFE_COMMANDS = {"dir", "ls", "echo", "type", "cat", "ipconfig", "systeminfo", "tasklist", "ping", "uptime"}
BLOCKED_KEYWORDS = {"rm", "del", "format", "mkfs", "shutdown", "reboot", "powershell", "kill"}

async def run_command(command: str) -> str:
    """Execute a shell command on the host."""
    base_cmd = command.split()[0].lower() if command.split() else ""
    if any(keyword in command.lower() for keyword in BLOCKED_KEYWORDS):
        return "Error: Command contains blocked keyword for safety."
    if base_cmd not in SAFE_COMMANDS:
        return f"Error: '{base_cmd}' is not in the whitelist."

    try:
        nexus_log(f"Executing command: {command}", level="system")
        process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if process.returncode == 0:
            return f"Output:\n{process.stdout[:800]}"
        return f"Error ({process.returncode}):\n{process.stderr[:400]}"
    except Exception as e:
        nexus_log(f"Command failed: {str(e)}", level="error")
        return f"Execution Error: {str(e)}"

async def open_application(app_name: str) -> str:
    """Opens a Windows application."""
    try:
        subprocess.Popen(f"start {app_name}", shell=True)
        return f"Success: Opening {app_name}."
    except Exception as e:
        return f"Error: {str(e)}"

# --- Data/Memory Tools ---
async def create_task(user_id: str, title: str, priority: str = "medium", due_date: str = None) -> str:
    """Saves a task to Firestore."""
    await memory_service.save_task(user_id, {"title": title, "priority": priority, "due_date": due_date})
    return f"Success: Task '{title}' saved."

async def create_note(user_id: str, title: str, content: str) -> str:
    """Saves a personal note or memo."""
    await memory_service.save_note(user_id, {"title": title, "content": content})
    return f"Success: Note '{title}' saved."

async def web_search(query: str, max_results: int = 5) -> str:
    """Performs a web search to retrieve real-time information."""
    logger.info(f"Searching for: {query}")
    nexus_log(f"Searching web for: {query}", level="info")
    try:
        results = []
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=max_results):
            results.append(f"Title: {r['title']}\nSource: {r['href']}\nSnippet: {r['body']}\n")
        
        if not results:
            return "No results found for your query."
        
        return "\n---\n".join(results)
    except Exception as e:
        logger.error(f"Search error: {e}")
        nexus_log(f"Search failed: {str(e)}", level="error")
        return f"Error during search: {str(e)}"

# --- Tool Metadata ---
NEXUS_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a safe shell command on the local system.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a Windows application by name.",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Save a personal note or memo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time information, news, or facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "max_results": {"type": "integer", "description": "Number of results to return (default 5)"}
                },
                "required": ["query"]
            }
        }
    }
]
