import asyncio
import logging
from typing import Dict, Any
from core.database import db

logger = logging.getLogger("nexus.verification")

async def verify_feature(feature: str, status: str, result: str, evidence: str) -> None:
    """
    Log a verification result to the database (Rule 8).
    status should be 'PASS', 'FAIL', or 'PENDING'.
    """
    try:
        await db.log_verification(feature, status, result, evidence)
        logger.info(f"✅ [Verification] {feature} -> {status}: {result}")
    except Exception as e:
        logger.error(f"❌ Failed to log verification for {feature}: {e}")

async def get_all_verifications() -> list:
    """
    Get all verification results from the database.
    """
    try:
        return await db.get_verification_status()
    except Exception as e:
        logger.error(f"❌ Failed to get verifications: {e}")
        return []

def verify_feature_sync(feature: str, status: str, result: str, evidence: str) -> None:
    """
    Synchronous wrapper for verifying a feature, useful in non-async contexts.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(verify_feature(feature, status, result, evidence))
    except RuntimeError:
        asyncio.run(verify_feature(feature, status, result, evidence))
