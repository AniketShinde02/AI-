from core.registry import tool_registry

# Import all tool functions
from .file_tools import read_file, write_file, read_directory, search_files
from .third_party_tools import get_weather, search_web, read_webpage

# Register tools with explicit roles
tool_registry.register("read_file", read_file, required_roles=["admin"])
tool_registry.register("write_file", write_file, required_roles=["admin"])
tool_registry.register("read_directory", read_directory, required_roles=["admin"])
tool_registry.register("search_files", search_files, required_roles=["admin"])


tool_registry.register("get_weather", get_weather, required_roles=["user", "admin"])
tool_registry.register("search_web", search_web, required_roles=["user", "admin"])
tool_registry.register("read_webpage", read_webpage, required_roles=["user", "admin"])

__all__ = [
    "tool_registry"
]
