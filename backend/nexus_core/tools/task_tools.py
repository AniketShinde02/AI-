import logging
from typing import Dict, Any, List

logger = logging.getLogger("nexus.tools.tasks")

# This will be injected by the LLM runner
memory_engine = None

async def create_task(title: str, priority: str = "medium", due_date: str = None) -> Dict[str, Any]:
    """
    Creates a new task in the user's task list.
    Args:
        title: The task description or title.
        priority: high, medium, or low.
        due_date: Optional due date string.
    """
    if not memory_engine:
        return {"success": False, "verified": False, "result": "", "error": "Error: Memory engine not initialized."}

    task_data = {
        "title": title,
        "priority": priority,
        "due_date": due_date,
        "type": "task"
    }
    
    logger.info(f"📌 Creating task: {title} ({priority})")
    await memory_engine.save_task(task_data)
    return {"success": True, "verified": True, "result": f"Success: Task '{title}' has been created and added to your list.", "error": None}

async def create_note(title: str, content: str) -> Dict[str, Any]:
    """
    Saves a new note or memo.
    Args:
        title: Short title for the note.
        content: The full content or body of the note.
    """
    if not memory_engine:
        return {"success": False, "verified": False, "result": "", "error": "Error: Memory engine not initialized."}

    note_data = {
        "title": title,
        "content": content,
        "type": "note"
    }
    
    logger.info(f"🗒️ Saving note: {title}")
    await memory_engine.save_note(note_data)
    return {"success": True, "verified": True, "result": f"Success: Note '{title}' has been saved.", "error": None}

# Tool definitions for the LLM
TASK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task or todo item for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task title or description."},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "Optional due date (e.g. 'tomorrow', 'Friday')."}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Save a personal note, memo, or piece of information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A short descriptive title for the note."},
                    "content": {"type": "string", "description": "The full text content of the note."}
                },
                "required": ["title", "content"]
            }
        }
    }
]
