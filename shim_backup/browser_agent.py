"""
browser_agent.py — Backward Compatibility Shim
================================================
This module exists ONLY to preserve import compatibility for all existing
callers (voice_session, executors, task_cards, etc.) while the browser domain
has been refactored into core/browser/.

DO NOT add logic here. All behavior lives in core/browser/facade.py.
"""
from core.browser.facade import BrowserAgent
from core.browser.session.pool import session_pool
from core.browser.models import BrowserMemory, BrowserStateEnum

# Singleton — mirrors the old `browser_agent = BrowserAgent()` global
browser_agent = BrowserAgent()

__all__ = ["BrowserAgent", "browser_agent", "BrowserMemory", "BrowserStateEnum", "session_pool"]
