import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger("nexus.tools.files")

async def read_file(file_path: str) -> str:
    """Read the text content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"File Content:\n{content[:2000]}" # Truncate long files
    except Exception as e:
        return f"Error reading file: {str(e)}"

async def write_file(file_name: str, content: str) -> str:
    """Write text to a file (creates or overwrites)."""
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_name}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

async def read_directory(directory_path: str) -> str:
    """Scan a directory to see what files are inside."""
    try:
        if not os.path.isdir(directory_path):
            return f"Error: {directory_path} is not a valid directory."
        
        items = os.listdir(directory_path)
        output = [f"Contents of {directory_path}:"]
        for item in items[:50]: # Limit to 50 items
            path = os.path.join(directory_path, item)
            size = os.path.getsize(path) if os.path.isfile(path) else 0
            item_type = "File" if os.path.isfile(path) else "Dir"
            output.append(f"- [{item_type}] {item} ({size} bytes)")
        
        if len(items) > 50:
            output.append("... (truncated)")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error reading directory: {str(e)}"

FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text to a file (creates or overwrites).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "File name (e.g. notes.txt) or full path."
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write."
                    }
                },
                "required": ["file_name", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_directory",
            "description": "Scan a directory (folder) to see what files are inside.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The folder path (e.g. 'Desktop', 'Documents', 'C:/Projects')."
                    }
                },
                "required": ["directory_path"]
            }
        }
    }
]
