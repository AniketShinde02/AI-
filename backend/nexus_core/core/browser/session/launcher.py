"""
browser/session/launcher.py
============================
Nexus Browser Domain — Browser Launcher

Single Responsibility: Resolve the correct browser executable and launch a
Playwright persistent context. Zero knowledge of BrowserAgent actions.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from core.browser.session.context import SessionContext

logger = logging.getLogger("nexus.browser.launcher")

_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1280,720",
    "--disable-features=IsolateOrigins,site-per-process",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def launch_session(session: SessionContext) -> Any:
    """
    Start a Playwright browser context for the given session.
    Returns the active Playwright Page.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    from core.browser.session.resolver import resolve_browser
    from core.browser.prompts import STEALTH_JS

    browser_hint = session.memory.browser_hint
    exe_path, channel, is_fallback, user_data_dir = resolve_browser(user_hint=browser_hint)
    if is_fallback:
        logger.warning("[Launcher] Using fallback browser (bundled Chromium)")

    session._playwright = await async_playwright().start()
    browser_driver = getattr(session._playwright, channel, session._playwright.chromium)

    # CDP Attachment Strategy (Issue 5: Native Browser Ownership)
    cdp_connected = False
    try:
        import urllib.request
        # Check if port is open before trying playwright to avoid long timeouts
        urllib.request.urlopen("http://localhost:9222/json/version", timeout=1)
        session._browser = await browser_driver.connect_over_cdp("http://localhost:9222")
        session._context = session._browser.contexts[0] if session._browser.contexts else await session._browser.new_context()
        logger.info("[Launcher] Attached to existing native browser via CDP on port 9222")
        cdp_connected = True
    except Exception as e:
        logger.info(f"[Launcher] CDP attach failed or no browser listening (port 9222).")
        if exe_path and user_data_dir:
            logger.info(f"[Launcher] Launching native browser via subprocess: {exe_path}")
            import subprocess
            subprocess.Popen([
                exe_path, 
                f"--remote-debugging-port=9222", 
            ])
            import asyncio
            await asyncio.sleep(2.5)  # Wait for browser to start
            try:
                session._browser = await browser_driver.connect_over_cdp("http://localhost:9222")
                session._context = session._browser.contexts[0] if session._browser.contexts else await session._browser.new_context()
                logger.info("[Launcher] Attached to newly launched native browser via CDP")
                cdp_connected = True
            except Exception as e2:
                logger.warning(f"Failed to attach to newly launched native browser: {e2}")

    # Fallback to isolated persistent context if CDP failed
    if not cdp_connected:
        logger.warning("[Launcher] Falling back to isolated Playwright persistent context.")
        os.makedirs(session.profile_dir, exist_ok=True)
        launch_kwargs: dict = dict(
            headless=False, # We want to see it now
            args=_LAUNCH_ARGS,
            viewport={"width": 1280, "height": 720},
            user_agent=_USER_AGENT,
        )
        if exe_path:
            launch_kwargs["executable_path"] = exe_path

        session._context = await browser_driver.launch_persistent_context(
            session.profile_dir, **launch_kwargs
        )

    try:
        await session._context.add_init_script(STEALTH_JS)
    except Exception as e:
        logger.debug(f"Could not add init script to CDP context: {e}")

    # Multi-tab: track popup/new-tab pages automatically
    session._context.on("page", lambda new_page: setattr(session, "_page", new_page))

    session._page = (
        session._context.pages[-1]
        if session._context.pages
        else await session._context.new_page()
    )

    # Hydrate memory from DB if session was seen before
    try:
        from core.database import db
        db_session = await db.get_browser_session(session.session_id)
        if db_session:
            session.memory.current_url = db_session["current_url"]
            session.memory.page_title = db_session["page_title"]
            session.memory.last_action = db_session["last_action"]
            session.memory.session_state = db_session["session_state"]
    except Exception as e:
        logger.debug(f"DB hydration failed for session {session.session_id}: {e}")

    return session._page
