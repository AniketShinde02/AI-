"""
browser_launcher.py
===================
Nexus BrowserAgent V1.1 — System Browser Detection

Resolves the user's default browser from the Windows Registry and maps it
to a Playwright-automatable channel.

Playwright can only drive Chromium-family browsers natively (chrome, msedge, brave).
If the default browser is Firefox or Safari, falls back to bundled chromium.

Priority:
  1. User-specified browser (e.g. "use brave", "use edge")
  2. System default browser (Windows Registry)
  3. Bundled Chromium (fallback)
"""
import os
import logging
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger("nexus.browser_launcher")

# Known automatable Chromium-family browsers
_CHROMIUM_FAMILY = {
    "chrome": {
        "paths": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "channel": "chrome",
    },
    "brave": {
        "paths": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
        "channel": "chromium",  # Playwright uses chromium channel for Brave
    },
    "msedge": {
        "paths": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "channel": "msedge",
    },
    "chromium": {
        "paths": [],  # bundled — no executable_path needed
        "channel": "chromium",
    },
}

# Browsers that Playwright CANNOT automate via chromium driver
_NON_AUTOMATABLE = {"firefox", "iexplore", "safari", "opera"}

# Map of keyword → browser key
_BROWSER_KEYWORDS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "brave": "brave",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "chromium": "chromium",
    "firefox": None,  # unsupported — will warn + fallback
    "opera": None,
}


def _get_windows_default_browser() -> Optional[str]:
    """
    Reads the user's default browser from Windows Registry.
    Returns browser key: 'chrome', 'brave', 'msedge', 'firefox', etc.
    Returns None if undetectable.
    """
    try:
        import winreg
        # Query default browser ProgID
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            prog_id = prog_id.lower()

        if "chrome" in prog_id:
            return "chrome"
        elif "brave" in prog_id:
            return "brave"
        elif "edge" in prog_id or "msedge" in prog_id:
            return "msedge"
        elif "firefox" in prog_id:
            return "firefox"
        elif "opera" in prog_id:
            return "opera"
        else:
            logger.debug(f"[BrowserLauncher] Unknown ProgId: {prog_id}, falling back to chromium")
            return "chromium"
    except Exception as e:
        logger.warning(f"[BrowserLauncher] Registry read failed: {e}, falling back to chromium")
        return "chromium"


def _find_executable(browser_key: str) -> Optional[str]:
    """Return first found executable path for a browser key."""
    entry = _CHROMIUM_FAMILY.get(browser_key)
    if not entry:
        return None
    for path in entry.get("paths", []):
        if os.path.isfile(path):
            return path
    return None


def resolve_browser(user_hint: Optional[str] = None) -> Tuple[Optional[str], str, bool]:
    """
    Resolve which browser to launch.

    Args:
        user_hint: Optional string from user command e.g. "brave", "chrome", "edge"

    Returns:
        (executable_path, playwright_channel, is_fallback)
        - executable_path: None means use Playwright's bundled browser
        - playwright_channel: 'chromium', 'chrome', or 'msedge'
        - is_fallback: True if we had to fall back from user's preference
    """
    # 1. User explicitly requested a browser
    if user_hint:
        hint_lower = user_hint.lower().strip()
        for keyword, browser_key in _BROWSER_KEYWORDS.items():
            if keyword in hint_lower:
                if browser_key is None:
                    logger.warning(
                        f"[BrowserLauncher] '{user_hint}' cannot be automated by Playwright. "
                        f"Falling back to bundled Chromium."
                    )
                    return None, "chromium", True

                exe = _find_executable(browser_key)
                channel = _CHROMIUM_FAMILY[browser_key]["channel"]
                if exe:
                    logger.info(f"[BrowserLauncher] User requested '{user_hint}' → {exe}")
                    return exe, channel, False
                else:
                    logger.warning(
                        f"[BrowserLauncher] '{user_hint}' not found at expected paths. "
                        f"Falling back to bundled Chromium."
                    )
                    return None, "chromium", True

    # 2. System default browser
    default = _get_windows_default_browser()
    logger.info(f"[BrowserLauncher] System default browser detected: {default}")

    if default in _NON_AUTOMATABLE:
        logger.warning(
            f"[BrowserLauncher] Default browser '{default}' cannot be automated. "
            f"Using bundled Chromium."
        )
        return None, "chromium", True

    if default and default in _CHROMIUM_FAMILY:
        exe = _find_executable(default)
        channel = _CHROMIUM_FAMILY[default]["channel"]
        if exe:
            logger.info(f"[BrowserLauncher] Using system default: {exe}")
            return exe, channel, False

    # 3. Final fallback: bundled Chromium
    logger.info("[BrowserLauncher] Using Playwright bundled Chromium")
    return None, "chromium", False
