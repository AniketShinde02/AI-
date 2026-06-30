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

class VerificationEngine:
    async def verify_action(self, tool_id: str, target: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses VisionParser to take a screenshot and visually verify if the tool action succeeded.
        """
        try:
            from core.desktop.control import pc_controller
            import uuid
            import os
            import base64
            from io import BytesIO
            from PIL import ImageGrab
            from core.vision.parser import vision_parser

            logger.info(f"🔍 [VerificationEngine] Capturing screen to verify {tool_id}({target})")
            
            # 1. Grab screenshot
            img = ImageGrab.grab(all_screens=True)
            buffered = BytesIO()
            img.convert('RGB').save(buffered, format="JPEG", quality=80)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # 2. Formulate verification prompt
            prompt = (
                f"You are the Nexus Verification Engine. I just executed the desktop action '{tool_id}' "
                f"with target '{target}'. Look at the current screen. Did this action succeed? "
                f"Respond with a strict JSON object: {{\"verified\": true/false, \"reason\": \"your explanation\"}}"
            )
            
            # 3. Analyze
            analysis = await vision_parser.analyze_screenshot(img_str, prompt=prompt, use_som=False)
            
            # 4. Parse JSON
            import json
            import re
            json_match = re.search(r"\{.*\}", analysis, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {
                    "verified": bool(data.get("verified", False)),
                    "reason": data.get("reason", analysis)
                }
            else:
                return {"verified": False, "reason": "Could not parse JSON from Vision model: " + analysis}
                
        except Exception as e:
            logger.error(f"VerificationEngine failed: {e}")
            return {"verified": False, "reason": str(e)}

verification_engine = VerificationEngine()
