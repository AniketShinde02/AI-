import asyncio
import logging
from typing import Any
from unittest.mock import patch

logger = logging.getLogger("nexus.tests.failure_injector")

class FailureInjector:
    """
    Actively sabotages Nexus during test runs to prove the recovery systems work.
    """
    
    @staticmethod
    async def sabotage_api_rate_limit(duration_seconds: float = 3.0):
        """
        Force a fake 429 response from the underlying ModelRouter.
        """
        logger.warning("💉 [Injector] Injecting Fake 429 API Rate Limit...")
        
        original_route = None
        try:
            from core.model_router import model_router
            original_route = model_router.route_task
            
            async def fake_route_task(*args, **kwargs):
                raise Exception("429 Too Many Requests: Rate limit exceeded (Injected)")
                
            model_router.route_task = fake_route_task
            
            await asyncio.sleep(duration_seconds)
            
        finally:
            if original_route:
                from core.model_router import model_router
                model_router.route_task = original_route
                logger.info("💉 [Injector] Removed Fake 429 Injection.")

    @staticmethod
    async def sabotage_browser_crash(session_id: str):
        """
        Forcefully close the Playwright page context to simulate a crash.
        """
        logger.warning(f"💉 [Injector] Crashing Browser for session {session_id}...")
        try:
            from core.browser_agent import BrowserAgent
            agent = BrowserAgent()
            session = agent._get_session(session_id)
            if session._page and not session._page.is_closed():
                await session._page.close()
                logger.info("💉 [Injector] Browser successfully crashed.")
            else:
                logger.info("💉 [Injector] Browser was already closed.")
        except Exception as e:
            logger.error(f"💉 [Injector] Failed to crash browser: {e}")
