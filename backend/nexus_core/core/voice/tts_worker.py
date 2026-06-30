"""
session_tts_worker.py
---------------------
Responsibility: TTS worker, metrics worker, greeting flow, and audio delivery helpers.
Extracted from voice_session.py.

DO NOT import from voice_session.py here.
"""
import asyncio
import base64
import logging
import pickle
import platform
import random
import re
import time

import psutil
from fastapi import WebSocketDisconnect

import core.global_state as gs
from providers.tts import ProviderStatus

logger = logging.getLogger("nexus_ws")


class SessionTTSMixin:
    """
    Mixin that owns the TTS worker loop, metrics broadcaster, and greeting.

    Expects host class to expose:
      self.websocket, self.is_connected, self.session_id, self.current_turn_id,
      self.current_chunk_index, self.agent_is_speaking, self.last_agent_speech_time,
      self.tts_queue, self.state, self.selected_persona, self.selected_language,
      self.post_tts_guard_time, self.post_tts_guard_until, self.has_greeted,
      self.echo_window_active, self.echo_window_start,
      self.stt_latency, self.llm_latency,
      self.safe_send_json(), self._change_state(), enqueue_tts()
    """

    # -----------------------------------------------------------------
    # Safe WebSocket send helpers
    # -----------------------------------------------------------------

    async def safe_send_json(self, data: dict):
        if not self.is_connected:  # type: ignore[attr-defined]
            raise WebSocketDisconnect()
        try:
            await self.websocket.send_json(data)  # type: ignore[attr-defined]
        except Exception:
            self.is_connected = False  # type: ignore[attr-defined]
            raise WebSocketDisconnect()

    async def safe_send_bytes(self, data: bytes):
        if not self.is_connected:  # type: ignore[attr-defined]
            raise WebSocketDisconnect()
        try:
            await self.websocket.send_bytes(data)  # type: ignore[attr-defined]
        except Exception:
            self.is_connected = False  # type: ignore[attr-defined]
            raise WebSocketDisconnect()

    # -----------------------------------------------------------------
    # TTS queue enqueue helper
    # -----------------------------------------------------------------

    async def enqueue_tts(self, text: str, turn_id: int, is_last: bool = False):
        """Adds a semantic chunk to the TTS queue."""
        self.tts_queue.put_nowait({  # type: ignore[attr-defined]
            "text": text,
            "turn_id": turn_id,
            "index": self.current_chunk_index + 1,  # type: ignore[attr-defined]
        })

    # -----------------------------------------------------------------
    # Stop audio
    # -----------------------------------------------------------------

    async def stop_audio(self) -> None:
        """Immediately stops any ongoing TTS and clears buffers."""
        self.agent_is_speaking = False  # type: ignore[attr-defined]
        self.audio_buffer.clear()  # type: ignore[attr-defined]
        while not self.tts_queue.empty():  # type: ignore[attr-defined]
            try:
                self.tts_queue.get_nowait()  # type: ignore[attr-defined]
            except asyncio.QueueEmpty:
                break
        logger.info("🛑 [Stop Audio] Audio generation and buffers cleared.")

    # -----------------------------------------------------------------
    # TTS worker
    # -----------------------------------------------------------------

    async def tts_worker(self):
        """Background worker — synthesizes and sends audio sequentially from the queue."""
        logger.debug("👷 TTS Worker started.")
        try:
            while self.is_connected:  # type: ignore[attr-defined]
                item = await self.tts_queue.get()  # type: ignore[attr-defined]
                if item is None:
                    break

                if gs.tts_router is None or gs.tts_router.status != ProviderStatus.READY:
                    logger.error("❌ [Worker] TTS router not ready. Waiting...")
                    await asyncio.sleep(1)
                    self.tts_queue.put_nowait(item)  # type: ignore[attr-defined]
                    self.tts_queue.task_done()  # type: ignore[attr-defined]
                    continue

                text       = item.get("text", "")
                turn_id    = item.get("turn_id", 0)

                if turn_id != self.current_turn_id:  # type: ignore[attr-defined]
                    logger.info(f"🗑 [Worker] Skipping stale chunk from Turn {turn_id}")
                    self.tts_queue.task_done()  # type: ignore[attr-defined]
                    continue

                if item.get("is_sentinel"):
                    logger.info(f"🏁 [Worker] All audio for Turn {turn_id} sent. Signaling tts_end.")
                    if self.is_connected and turn_id == self.current_turn_id:  # type: ignore[attr-defined]
                        await self.safe_send_json({"type": "tts_end", "turn_id": turn_id})
                    self.tts_queue.task_done()  # type: ignore[attr-defined]
                    continue

                try:
                    self.agent_is_speaking = True  # type: ignore[attr-defined]
                    if gs.tts_router is None:
                        logger.error("❌ [Worker] TTS router is None")
                        break

                    kwargs = {
                        "gender":   self.selected_persona,   # type: ignore[attr-defined]
                        "language": self.selected_language,   # type: ignore[attr-defined]
                    }
                    provider_name = "edge"
                    is_indian = (
                        bool(re.search(r'[\u0900-\u097f]', text))
                        or self.selected_language in ["hi", "mr"]  # type: ignore[attr-defined]
                    )
                    if is_indian and self.selected_language != "mr":  # type: ignore[attr-defined]
                        kwargs["language"] = "hi"
                    elif is_indian:
                        kwargs["language"] = "mr"
                    else:
                        kwargs["language"] = "en"

                    tts_start_time = time.perf_counter()
                    audio_gen = gs.tts_router.stream_audio(text, provider=provider_name, **kwargs)

                    if audio_gen:
                        audio_buffer = b""
                        BUFFER_SIZE = 6400  # ~200ms @ 16kHz s16le

                        async for pcm_data in audio_gen:
                            if not self.is_connected or turn_id != self.current_turn_id:  # type: ignore[attr-defined]
                                logger.info("⏹ [Worker] Turn superseded or disconnected, stopping...")
                                break

                            if isinstance(pcm_data, dict):
                                logger.info(f"🔄 [TTS] Routing metadata: {pcm_data}")
                                continue

                            audio_buffer += pcm_data.samples.tobytes()

                            if len(audio_buffer) >= BUFFER_SIZE:
                                from core.workspace.state import SessionState
                                if self.state != SessionState.SPEAKING:  # type: ignore[attr-defined]
                                    tts_latency = time.perf_counter() - tts_start_time
                                    total_latency = time.perf_counter() - self.turn_start_time  # type: ignore[attr-defined]
                                    logger.info(f"[STT] {self.stt_latency*1000:.0f}ms")  # type: ignore[attr-defined]
                                    logger.info(f"[LLM] {self.llm_latency*1000:.0f}ms")  # type: ignore[attr-defined]
                                    logger.info(f"[TTS] {tts_latency*1000:.0f}ms")
                                    logger.info(f"[TOTAL] {total_latency*1000:.0f}ms")
                                    self._change_state(SessionState.SPEAKING)  # type: ignore[attr-defined]
                                    self.echo_window_active = True  # type: ignore[attr-defined]
                                    self.echo_window_start = time.time()  # type: ignore[attr-defined]
                                    logger.info("📢 [Audio] Agent speech started. Echo window active.")

                                self.current_chunk_index += 1  # type: ignore[attr-defined]
                                await self.safe_send_json({
                                    "type": "audio_chunk",
                                    "data": base64.b64encode(audio_buffer).decode("utf-8"),
                                    "meta": {
                                        "turn_id": turn_id,
                                        "chunk_index": self.current_chunk_index,  # type: ignore[attr-defined]
                                        "is_last": False,
                                    }
                                })
                                audio_buffer = b""
                                self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]

                        # Send final remaining bytes
                        if self.is_connected and turn_id == self.current_turn_id:  # type: ignore[attr-defined]
                            self.current_chunk_index += 1  # type: ignore[attr-defined]
                            await self.safe_send_json({
                                "type": "audio_chunk",
                                "data": base64.b64encode(audio_buffer).decode("utf-8"),
                                "meta": {
                                    "turn_id": turn_id,
                                    "chunk_index": self.current_chunk_index,  # type: ignore[attr-defined]
                                    "is_last": False,
                                }
                            })
                            self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]
                            self.post_tts_guard_until = (  # type: ignore[attr-defined]
                                time.time() + self.post_tts_guard_time  # type: ignore[attr-defined]
                            )
                            logger.debug(
                                f"🛡️ [Guard] Post-TTS echo guard armed for "
                                f"{self.post_tts_guard_time}s"  # type: ignore[attr-defined]
                            )

                except Exception as e:
                    logger.error(f"❌ [Worker] Error synthesizing Turn {turn_id}: {e}")
                    if self.is_connected:  # type: ignore[attr-defined]
                        await self.safe_send_json({
                            "type": "error",
                            "message": f"Speech synthesis failed: {e}"
                        })
                finally:
                    self.tts_queue.task_done()  # type: ignore[attr-defined]

        except Exception as e:
            logger.error(f"❌ TTS Worker crashed: {e}")
        finally:
            logger.debug("👷 TTS Worker stopped.")

    # -----------------------------------------------------------------
    # Metrics worker
    # -----------------------------------------------------------------

    async def metrics_worker(self):
        """Streams system metrics to the client every 1.5 seconds.

        ⚠️  DO NOT remove the inner try/except around safe_send_json.
        During uvicorn hot-reload, this loop can outlive the WebSocket connection.
        A bare send to a dead socket raises RuntimeError (not CancelledError),
        which previously caused 'Metrics Worker crashed: ' errors in the logs.
        The fix: catch any send-level exception and break cleanly.
        """
        logger.debug("📊 Metrics Worker started.")
        try:
            while self.is_connected:  # type: ignore[attr-defined]
                await asyncio.sleep(1.5)
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                os_name = f"{platform.system()} {platform.release()}"
                temp = min((cpu / 100.0) * 40 + 40 + random.uniform(-2, 2), 90.0)
                ping = random.randint(12, 45)
                rate = round(random.uniform(0.5, 9.0), 2)
                tx = random.randint(0, 100)
                rx = random.randint(0, 100)

                metrics = {
                    "cpu": cpu,
                    "memory": {"usedPercentage": mem},
                    "temperature": round(temp, 1),
                    "os": {"type": os_name},
                    "network": {"ping": ping, "rate": rate, "tx": tx, "rx": rx}
                }

                if self.is_connected:  # type: ignore[attr-defined]
                    try:
                        await self.safe_send_json({"type": "system_metrics", "data": metrics})
                    except Exception:
                        # WS is dead (hot-reload, client disconnect, etc.) — exit quietly.
                        break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Metrics Worker crashed: {e}")
        finally:
            logger.debug("📊 Metrics Worker stopped.")

    # -----------------------------------------------------------------
    # Greeting
    # -----------------------------------------------------------------

    async def greet(self):
        """Sends an initial greeting when connected. Uses cached PCM if available."""
        if self.has_greeted:  # type: ignore[attr-defined]
            logger.info("👋 Skipping greeting (already greeted this session)")
            return

        text = "Hi, I'm Nexus. How can I help you today?"
        logger.info(f"👋 Sending greeting: {text}")

        try:
            self.agent_is_speaking = True  # type: ignore[attr-defined]
            self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]
            greeting_turn_id = 0
            await self.safe_send_json({"type": "agent_message", "text": text})

            async with gs.greeting_lock:
                if gs.cached_greeting_pcm:
                    logger.info("👋 Sending cached greeting PCM")
                    for i, chunk in enumerate(gs.cached_greeting_pcm):
                        if not self.is_connected: 
                            break  # type: ignore[attr-defined]
                        await self.safe_send_json({
                            "type": "audio_chunk",
                            "data": base64.b64encode(chunk).decode("utf-8"),
                            "meta": {"turn_id": greeting_turn_id, "chunk_index": i}
                        })
                        self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]

                    if self.is_connected:  # type: ignore[attr-defined]
                        await self.safe_send_json({"type": "tts_end", "turn_id": greeting_turn_id})
                    self.has_greeted = True  # type: ignore[attr-defined]
                    return

                # Synthesize and cache
                full_pcm = []
                if gs.tts_router is not None:
                    if not await gs.tts_router.wait_until_ready(timeout=5.0):
                        logger.error("❌ [Pipeline] TTS providers failed to become ready in time.")
                        return

                    audio_gen = gs.tts_router.stream_audio(
                        text,
                        provider="edge",
                        gender=self.selected_persona,  # type: ignore[attr-defined]
                        language="en"
                    )
                    if audio_gen:
                        idx = 0
                        audio_buffer = b""
                        BUFFER_SIZE = 9600  # 200ms @ 24kHz s16

                        async for pcm_data in audio_gen:
                            if not self.is_connected: 
                                break  # type: ignore[attr-defined]
                            if isinstance(pcm_data, dict):
                                logger.info(f"🔄 [TTS Greet] Routing metadata: {pcm_data}")
                                continue
                            audio_buffer += pcm_data.samples.tobytes()
                            if len(audio_buffer) >= BUFFER_SIZE:
                                full_pcm.append(audio_buffer)
                                await self.safe_send_json({
                                    "type": "audio_chunk",
                                    "data": base64.b64encode(audio_buffer).decode("utf-8"),
                                    "meta": {"turn_id": greeting_turn_id, "chunk_index": idx, "is_last": False}
                                })
                                audio_buffer = b""
                                idx += 1
                                self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]

                        if audio_buffer and self.is_connected:  # type: ignore[attr-defined]
                            full_pcm.append(audio_buffer)
                            await self.safe_send_json({
                                "type": "audio_chunk",
                                "data": base64.b64encode(audio_buffer).decode("utf-8"),
                                "meta": {"turn_id": greeting_turn_id, "chunk_index": idx, "is_last": True}
                            })
                            self.last_agent_speech_time = time.time()  # type: ignore[attr-defined]

                        if self.is_connected:  # type: ignore[attr-defined]
                            await self.safe_send_json({"type": "tts_end", "turn_id": greeting_turn_id})
                    else:
                        logger.error("❌ [Pipeline] TTS provider returned None during greeting")

                    if full_pcm:
                        gs.cached_greeting_pcm = full_pcm
                        try:
                            with open(gs.CACHE_FILE, "wb") as f:
                                pickle.dump(gs.cached_greeting_pcm, f)
                        except Exception as e:
                            logger.error(f"❌ Failed to save greeting cache: {e}")
                    else:
                        logger.warning("⚠️ No TTS audio generated, not updating cache.")

                    self.has_greeted = True  # type: ignore[attr-defined]
                else:
                    logger.error("❌ [Pipeline] TTS router is None during greeting")

        except WebSocketDisconnect:
            logger.warning("🔌 Client disconnected during greeting")
            self.is_connected = False  # type: ignore[attr-defined]
            raise
        except Exception as e:
            logger.error(f"❌ Greeting Error: {e}")
            self.agent_is_speaking = False  # type: ignore[attr-defined]
