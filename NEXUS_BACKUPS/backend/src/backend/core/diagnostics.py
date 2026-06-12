import os
import sys
import json
from loguru import logger
from ..config.settings import settings

def check_environment():
    """Performs a deep diagnostic of the backend environment."""
    logger.info("[Diagnostics] Running Nexus 2.0 Backend Diagnostics...")
    
    issues = []
    
    # 1. Check API Keys
    api_keys = {
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GETSTREAM_API_KEY": settings.GETSTREAM_API_KEY,
        "GETSTREAM_API_SECRET": settings.GETSTREAM_API_SECRET,
        "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
        "ELEVENLABS_API_KEY": settings.ELEVENLABS_API_KEY,
    }
    
    for key, value in api_keys.items():
        if not value:
            logger.error(f"[FAIL] {key} is missing!")
            issues.append(f"Missing {key}")
        else:
            logger.info(f"[PASS] {key} is configured.")

    # 2. Check Firebase
    logger.info("[Firebase] Checking Firebase Connection...")
    try:
        from .firebase_db import FirebaseDB
        db = FirebaseDB.get_db()
        if db:
            logger.info("[PASS] Firebase Connection: SUCCESS")
    except Exception as e:
        logger.error(f"[FAIL] Firebase Connection: FAILED - {e}")
        issues.append(f"Firebase error: {e}")

    # 3. Check Python Environment
    logger.info(f"[Env] Python Version: {sys.version}")
    logger.info(f"[Env] Executable: {sys.executable}")
    
    if issues:
        logger.warning(f"[Warning] Diagnostics found {len(issues)} potential issues.")
        for issue in issues:
            logger.warning(f"   - {issue}")
    else:
        logger.info("[Success] All systems operational (diagnostics passed).")

    return len(issues) == 0

if __name__ == "__main__":
    check_environment()
