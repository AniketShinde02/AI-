"""
browser/session/streaming.py
============================
Nexus Browser Domain — Screencast & CDP Streaming

Single Responsibility: Attach to a page via CDP to stream frames and handle
raw mouse/keyboard interactions if needed.
"""
import asyncio
import logging
import base64
from typing import Optional, Callable, Awaitable

logger = logging.getLogger("nexus.browser.streaming")


class BrowserStreamer:
    def __init__(self):
        self.cdp_session = None
        self._on_frame_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self._running = False

    async def start_screencast(self, page, on_frame: Callable[[str], Awaitable[None]]):
        """
        Starts a CDP screencast on the given Playwright Page.
        """
        if self._running:
            return

        try:
            self._on_frame_callback = on_frame
            self.cdp_session = await page.context.new_cdp_session(page)

            # Register the event listener for incoming frames
            self.cdp_session.on("Page.screencastFrame", self._handle_screencast_frame)

            await self.cdp_session.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 30, # Low quality to reduce bandwidth for telemetry
                "everyNthFrame": 2, # Halve the frame rate
            })
            self._running = True
            logger.info("🎬 [Streaming] Screencast started.")
        except Exception as e:
            logger.error(f"❌ [Streaming] Failed to start screencast: {e}")

    async def _handle_screencast_frame(self, event: dict):
        try:
            if not self._running or not self.cdp_session:
                return
            
            # Acknowledge the frame to continue receiving frames
            session_id = event.get("sessionId")
            if session_id:
                # Use ensure_future to safely schedule coroutines
                asyncio.ensure_future(self.cdp_session.send("Page.screencastFrameAck", {"sessionId": session_id}))

            frame_b64 = event.get("data")
            if frame_b64 and self._on_frame_callback:
                asyncio.ensure_future(self._on_frame_callback(frame_b64))
        except Exception as e:
            logger.debug(f"[Streaming] Error handling frame: {e}")

    async def stop_screencast(self):
        self._running = False
        if self.cdp_session:
            try:
                await self.cdp_session.send("Page.stopScreencast")
                await self.cdp_session.detach()
            except Exception as e:
                logger.debug(f"[Streaming] Error stopping screencast: {e}")
            finally:
                self.cdp_session = None
                logger.info("⏹️ [Streaming] Screencast stopped.")

streamer = BrowserStreamer()
