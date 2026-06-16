import os
import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

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

IGNORE_FOLDERS = {
    'node_modules', 'appdata', 'program files', 'windows',
    'system volume information', 'dist', 'build', '.git', '$recycle.bin',
    '.next', 'venv', 'env'
}

def _native_search_sync(keywords: List[str], target_dir: str, max_results: int = 15) -> List[str]:
    """Synchronous heavy lifting for file searching to run in a thread."""
    found_files = []
    
    try:
        target_path = Path(target_dir).expanduser().resolve()
        if not target_path.exists():
            return []
            
        for root, dirs, files in os.walk(target_path):
            # In-place modification to skip ignored directories
            dirs[:] = [d for d in dirs if d.lower() not in IGNORE_FOLDERS and not d.startswith(('.', '$'))]
            
            for file in files:
                if len(found_files) >= max_results:
                    return found_files
                    
                file_lower = file.lower()
                # Check if ALL keywords match the file name
                is_match = all(kw.lower() in file_lower for kw in keywords)
                if is_match:
                    found_files.append(os.path.join(root, file))
                    
    except Exception as e:
        logger.error(f"Error during deep search: {e}")
        
    return found_files

async def search_files(keywords: List[str], search_root: str = "home") -> str:
    """
    Search for files locally using a native crawler.
    """
    try:
        # Determine the root
        if search_root.lower() in ["desktop", "documents", "downloads", "music", "pictures", "videos"]:
            base_dir = os.path.join(os.path.expanduser("~"), search_root.capitalize())
        elif search_root.lower() == "home":
            base_dir = os.path.expanduser("~")
        elif os.path.isabs(search_root):
            base_dir = search_root
        else:
            base_dir = os.path.join(os.path.expanduser("~"), search_root)
            
        logger.info(f"🔎 Sweeping {base_dir} for keywords: {keywords}")
        
        # Run the heavy IO-bound search in a separate thread so we don't block the WebSocket event loop
        found = await asyncio.to_thread(_native_search_sync, keywords, base_dir)
        
        if found:
            return f"⚡ Native Deep System Matches in {base_dir}:\n" + "\n".join([f"- {f}" for f in found])
        else:
            return f"No files found matching {keywords} in {base_dir}."
    except Exception as e:
        return f"Error searching files: {str(e)}"

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
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files locally on the user's computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to match in the filename (e.g. ['resume', 'pdf'])"
                    },
                    "search_root": {
                        "type": "string",
                        "description": "The root folder to search in (e.g., 'home', 'desktop', 'documents', 'downloads', or an absolute path). Defaults to 'home'."
                    }
                },
                "required": ["keywords"]
            }
        }
    }
]
