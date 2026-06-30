"""
browser/__init__.py
====================
Nexus Browser Domain — Public API

Only these symbols are part of the public interface.
No other module outside core/browser/ should import anything else directly.
"""
from core.browser.facade import BrowserAgent
from core.browser.models import BrowserStateEnum, BrowserMemory, ActionResult
from core.browser.session.pool import session_pool

__all__ = [
    "BrowserAgent",
    "BrowserStateEnum",
    "BrowserMemory",
    "ActionResult",
    "session_pool",
]
