from core.registry import tool_registry

# Import all tool functions
from .system import execute_pc_action
from .file_tools import read_file, write_file, read_directory, search_files
from .task_tools import create_task, create_note
from .memory_tools import update_preferences, get_user_memory, delete_user_preference
from .third_party_tools import get_weather, search_web, read_webpage

from .scrapper_tools import check_scrapper_health, list_available_scrapers, run_scrapper_task

# Register tools with explicit roles
tool_registry.register("execute_pc_action", execute_pc_action, required_roles=["admin"])
tool_registry.register("read_file", read_file, required_roles=["admin"])
tool_registry.register("write_file", write_file, required_roles=["admin"])
tool_registry.register("read_directory", read_directory, required_roles=["admin"])
tool_registry.register("search_files", search_files, required_roles=["admin"])

tool_registry.register("create_task", create_task, required_roles=["user", "admin"])
tool_registry.register("create_note", create_note, required_roles=["user", "admin"])
tool_registry.register("update_preferences", update_preferences, required_roles=["user", "admin"])
tool_registry.register("get_user_memory", get_user_memory, required_roles=["user", "admin"])
tool_registry.register("delete_user_preference", delete_user_preference, required_roles=["user", "admin"])
tool_registry.register("get_weather", get_weather, required_roles=["user", "admin"])
tool_registry.register("search_web", search_web, required_roles=["user", "admin"])
tool_registry.register("read_webpage", read_webpage, required_roles=["user", "admin"])
tool_registry.register("check_scrapper_health", check_scrapper_health, required_roles=["user", "admin"])
tool_registry.register("list_available_scrapers", list_available_scrapers, required_roles=["user", "admin"])
tool_registry.register("run_scrapper_task", run_scrapper_task, required_roles=["user", "admin"])

__all__ = [
    "tool_registry"
]
