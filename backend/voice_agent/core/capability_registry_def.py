"""
capability_registry_def.py
===========================
SINGLE SOURCE OF TRUTH for all Nexus V1 tool capability definitions.

Every capability must be defined here and ONLY here.
No scattered tool definitions elsewhere in the codebase.

Each entry is a CapabilityDef dataclass that covers:
  - Registry metadata (id, name, description, category, permissions)
  - Groq/OpenAI function-calling JSON schema
  - Confirmation label template (for TTS/UI confirmation speech)
  - Parameter key mapping (how action_router 'target' maps to the function param name)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class CapabilityDef:
    # --- Registry identity ---
    id: str                          # Unique tool_id (matches function name)
    name: str                        # Human-readable name
    description: str                 # Short description for UI and LLM
    category: str                    # Grouping category
    permissions_required: bool       # True → needs user approval in DB
    requires_approval: bool          # True → always prompt before execution
    enabled: bool = True             # Default enabled state

    # --- LLM Function-calling schema ---
    # Groq/OpenAI tools[] compatible dict
    groq_schema: Dict[str, Any] = field(default_factory=dict)

    # --- Dispatch ---
    # Which param key the action_router 'target' string maps to.
    # e.g. "app_name" for pc_open_app. None = no param injection (e.g. screenshot)
    target_param: Optional[str] = None

    # --- Confirmation speech ---
    # Template string. {target} is replaced by the title-cased target value.
    # If empty-string target, {target} may be omitted.
    confirm_template: str = "Done."


def _make_app_schema(tool_id: str, desc: str) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool_id,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application (e.g. 'notepad', 'chrome')"
                    }
                },
                "required": ["app_name"]
            }
        }
    }


# ============================================================
# CAPABILITY DEFINITIONS — all 15 Nexus V1 tools
# ============================================================

CAPABILITY_DEFINITIONS: List[CapabilityDef] = [

    # ── Desktop / Window Management ──────────────────────────

    CapabilityDef(
        id="pc_open_app",
        name="Open Application",
        description="Open a Windows application or file by name.",
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Opening {target}.",
        groq_schema=_make_app_schema("pc_open_app", "Open a Windows application or file."),
    ),

    CapabilityDef(
        id="pc_close_app",
        name="Close Application",
        description="Close a running Windows application by name.",
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Closing {target}.",
        groq_schema=_make_app_schema("pc_close_app", "Close a running Windows application by name."),
    ),

    CapabilityDef(
        id="pc_minimize_app",
        name="Minimize Application",
        description="Minimize a running Windows application window by name.",
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Minimizing {target}.",
        groq_schema=_make_app_schema("pc_minimize_app", "Minimize a running Windows application window."),
    ),

    CapabilityDef(
        id="pc_maximize_app",
        name="Maximize Application",
        description="Maximize a running Windows application window by name.",
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Maximizing {target}.",
        groq_schema=_make_app_schema("pc_maximize_app", "Maximize a running Windows application window."),
    ),

    CapabilityDef(
        id="pc_focus_app",
        name="Focus Application",
        description="Bring a running application window to the foreground / switch focus to it.",
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Switching to {target}.",
        groq_schema=_make_app_schema("pc_focus_app", "Bring a running application window to the foreground."),
    ),

    CapabilityDef(
        id="pc_switch_window",
        name="Switch Window",
        description=(
            "Switch to a named application window, or cycle windows with Alt+Tab if no name is provided."
        ),
        category="applications",
        permissions_required=False,
        requires_approval=False,
        target_param="app_name",
        confirm_template="Switching window.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_switch_window",
                "description": "Switch to a named app window, or cycle windows with Alt+Tab if no name given.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the app window to switch to. Leave empty to cycle via Alt+Tab."
                        }
                    },
                    "required": []
                }
            }
        },
    ),

    # ── Screenshot ────────────────────────────────────────────

    CapabilityDef(
        id="pc_take_screenshot",
        name="Take Screenshot",
        description="Capture the primary display and save as an image file.",
        category="screenshots",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Taking a screenshot.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_take_screenshot",
                "description": "Take a screenshot of the primary display.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
    ),

    # ── Keyboard ─────────────────────────────────────────────

    CapabilityDef(
        id="pc_type_text",
        name="Type Text",
        description="Simulate keyboard typing for the provided text string.",
        category="keyboard",
        permissions_required=False,
        requires_approval=False,
        target_param="text",
        confirm_template="Typed.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_type_text",
                "description": "Simulate keyboard typing for the provided text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The exact text to type"}
                    },
                    "required": ["text"]
                }
            }
        },
    ),

    CapabilityDef(
        id="pc_press_shortcut",
        name="Press Shortcut",
        description="Simulate a keyboard shortcut (e.g. Ctrl+C, Win+D).",
        category="keyboard",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Shortcut pressed.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_press_shortcut",
                "description": "Simulate a keyboard shortcut (e.g. ['ctrl', 'c']).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of keys to press together."
                        }
                    },
                    "required": ["keys"]
                }
            }
        },
    ),

    # ── Clipboard ────────────────────────────────────────────

    CapabilityDef(
        id="pc_clipboard_read",
        name="Clipboard Read",
        description="Read the current contents of the system clipboard.",
        category="clipboard",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Reading clipboard.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_clipboard_read",
                "description": "Read the current contents of the system clipboard.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
    ),

    CapabilityDef(
        id="pc_clipboard_write",
        name="Clipboard Write",
        description="Write or copy text to the system clipboard.",
        category="clipboard",
        permissions_required=False,
        requires_approval=False,
        target_param="text",
        confirm_template="Copied to clipboard.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "pc_clipboard_write",
                "description": "Write or copy text to the system clipboard.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to copy to the clipboard"}
                    },
                    "required": ["text"]
                }
            }
        },
    ),

    # ── Browser Capabilities ──────────────────────────────────

    CapabilityDef(
        id="browser_open_url",
        name="Open Browser URL",
        description="Open a specific URL in the browser.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="url",
        confirm_template="Opening {target}.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_open_url",
                "description": "Open a specific URL in the browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The full URL to open (e.g. https://google.com)"}
                    },
                    "required": ["url"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_search",
        name="Browser Search",
        description="Search the web for a specific query.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="query",
        confirm_template="Searching for {target}.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_search",
                "description": "Search the web for a specific query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search term"}
                    },
                    "required": ["query"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_click",
        name="Click Element",
        description="Click an element on the active page using CSS selector.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="selector",
        confirm_template="Clicked element.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Click an element on the currently controlled page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector to click"}
                    },
                    "required": ["selector"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_extract",
        name="Extract Page Text",
        description="Extract visible text from a webpage.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="url",
        confirm_template="Extracted text from {target}.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_extract",
                "description": "Extract visible text from a webpage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to extract text from"}
                    },
                    "required": ["url"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_screenshot",
        name="Browser Screenshot",
        description="Take a screenshot of the active browser page.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="url",
        confirm_template="Browser screenshot taken.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current page, or navigate to a URL first.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Optional URL to navigate to first."}
                    },
                    "required": []
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_type",
        name="Type In Browser",
        description="Type text into a specific element on the active browser page.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="selector",
        confirm_template="Typed text.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_type",
                "description": "Type text into a specific element. Clears the field first.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector to type into"},
                        "text": {"type": "string", "description": "The text to type"}
                    },
                    "required": ["selector", "text"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_submit",
        name="Submit Browser Form",
        description="Submit a form on the active page.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="selector",
        confirm_template="Form submitted.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_submit",
                "description": "Submit a form on the active page, optionally target a selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Optional CSS selector to trigger submission."}
                    },
                    "required": []
                }
            }
        },
    ),

    # ── Browser Tab Management ────────────────────────────────

    CapabilityDef(
        id="browser_tab_new",
        name="New Browser Tab",
        description="Open a new tab in the Nexus browser session.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="url",
        confirm_template="Opened a new tab.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_tab_new",
                "description": "Open a new tab in the browser. Optionally provide a URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Optional URL to open in the new tab."}
                    },
                    "required": []
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_tab_close",
        name="Close Browser Tab",
        description="Close the current or most recent tab in the Nexus browser session.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Closed the tab.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_tab_close",
                "description": "Close the current browser tab.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
    ),

    CapabilityDef(
        id="browser_tab_switch",
        name="Switch Browser Tab",
        description="Switch to a browser tab by integer index or by title match.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param="target",
        confirm_template="Switched tab.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_tab_switch",
                "description": "Switch to a browser tab by index (integer) or title (string).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Tab index (e.g. '0') or partial title to match."
                        }
                    },
                    "required": ["target"]
                }
            }
        },
    ),

    CapabilityDef(
        id="browser_tab_list",
        name="List Browser Tabs",
        description="List all currently open tabs in the Nexus browser session.",
        category="browser",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Listing open tabs.",
        groq_schema={
            "type": "function",
            "function": {
                "name": "browser_tab_list",
                "description": "List all open browser tabs.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
    ),

    # ── External Automation (ScrapperOS) ─────────────────────

    CapabilityDef(
        id="run_scrapper_task",
        name="Run ScrapperOS Task",
        description="Trigger an external web scraper task via the ScrapperOS bridge.",
        category="automation",
        permissions_required=True,
        requires_approval=True,
        target_param=None,
        confirm_template="ScrapperOS task triggered.",
        groq_schema={},  # Not exposed directly to LLM tool-calling
    ),

    CapabilityDef(
        id="list_available_scrapers",
        name="List Scrapers",
        description="Fetch the list of available web scrapers from ScrapperOS.",
        category="automation",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Listing available scrapers.",
        groq_schema={},
    ),

    CapabilityDef(
        id="check_scrapper_health",
        name="ScrapperOS Health",
        description="Check if the ScrapperOS automation service is online.",
        category="automation",
        permissions_required=False,
        requires_approval=False,
        target_param=None,
        confirm_template="Scrapper health checked.",
        groq_schema={},
    ),
]


# ============================================================
# Derived lookups — built once at import time, O(1) lookups
# ============================================================

# All capabilities indexed by id
CAPABILITY_MAP: Dict[str, CapabilityDef] = {cap.id: cap for cap in CAPABILITY_DEFINITIONS}

# Groq/OpenAI tool schemas for all capabilities that expose one
# (used by tools/system.py and tools/browser_tools.py)
PC_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    cap.groq_schema
    for cap in CAPABILITY_DEFINITIONS
    if cap.category not in ("browser", "automation") and cap.groq_schema
]

BROWSER_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    cap.groq_schema
    for cap in CAPABILITY_DEFINITIONS
    if cap.category == "browser" and cap.groq_schema
]

# Tuple of (id, name, desc, category, permissions_required, requires_approval)
# for bulk-registering in global_state.py lifespan
CAPABILITY_REGISTRATION_TUPLES = [
    (cap.id, cap.name, cap.description, cap.category, cap.permissions_required, cap.requires_approval)
    for cap in CAPABILITY_DEFINITIONS
]

# Confirmation labels dict — used by voice_session.py action_labels
# Keys match tool_id strings, values are template strings
CONFIRMATION_LABELS: Dict[str, str] = {
    cap.id: cap.confirm_template for cap in CAPABILITY_DEFINITIONS
}

# Action router tool name list — for the system prompt anchor
ACTION_ROUTER_TOOL_NAMES: List[str] = [
    cap.id for cap in CAPABILITY_DEFINITIONS
    if cap.category not in ("automation",) and cap.groq_schema
]
