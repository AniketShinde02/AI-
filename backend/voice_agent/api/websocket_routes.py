# ==========================================
# CRITICAL SYSTEM FILE
# Do not modify websocket lifecycle, session cleanup, 
# Gemini transport, or fallback routing without running 
# full voice test suite. Changes here can silently break voice.
# ==========================================
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import core.global_state as gs
from core.voice_session import VoiceSession, SessionState
import time
import asyncio

logger = logging.getLogger("nexus_ws")
ws_router = APIRouter()

@ws_router.websocket("/ws/nexus")
async def websocket_endpoint(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id")
    logger.info(f"🔌 Incoming WebSocket connection from {websocket.client} with session_id: {session_id}")
    await websocket.accept()
    logger.info("🔌 WebSocket connected and accepted")
    
    if session_id and session_id in gs.active_sessions:
        old_session = gs.active_sessions[session_id]
        old_session.is_connected = False
        logger.info(f"♻️ Replacing previous session {session_id} with a fresh one to restart worker tasks")
        
    session = VoiceSession(websocket, engine="nexus")
    if session_id:
        gs.active_sessions[session_id] = session
        logger.info(f"🆕 Created session {session_id}")

    try:
        # 5. Startup Greeting
        await session.greet()
        
        while session.is_connected:
            try:
                data = await websocket.receive()
                if "bytes" not in data: # Prevent logging massive binary payloads
                    text_data = data.get("text", "")
                    if text_data and '{"type":"ping"' not in text_data:
                        logger.debug(f"🔍 RAW WS RECEIVE: {data}")
            except (WebSocketDisconnect, RuntimeError):
                # RuntimeError = "Cannot call receive once a disconnect message has been received"
                break
            
            if "disconnect" in data:
                break
            elif "bytes" in data and data["bytes"] is not None:
                await session.process_audio(data["bytes"])
            elif "text" in data and data["text"] is not None:
                msg = json.loads(data["text"])
                if msg.get("type") == "vision_frame":
                    if session.gemini_manager and session.gemini_manager.is_connected:
                        await session.gemini_manager.send_video_frame(msg.get("data"))
                    continue

                if msg.get("type") == "ping":
                    await session.safe_send_json({
                        "type": "pong",
                        "timestamp": msg.get("timestamp")
                    })
                    continue

                if msg.get("type") == "audio_finished":
                    # Client reports playback complete.
                    session.agent_is_speaking = False
                    if session.state == SessionState.SPEAKING:
                        session._change_state(SessionState.IDLE)
                        session.post_tts_guard_until = time.time() + 1.2
                        logger.info(f"✅ [Session] audio_finished received. Armed post-TTS guard for 1.2s.")
                    else:
                        logger.info(f"ℹ️ [Session] audio_finished received in state: {session.state.value}. Cleared speaking flag.")
                    continue
                    
                if msg.get("type") == "settings":
                    logger.debug(f"📩 Received settings: {msg}")
                    session.selected_persona = msg.get("persona") or "female"
                    session.selected_provider = msg.get("ttsProvider") or "edge"
                    session.selected_language = msg.get("language") or "auto"
                    continue
                    
                if "action" in msg:
                    action = msg["action"]
                    logger.debug(f"📩 Received action: {action}")
                    if action == "mute":
                        session.is_muted = True
                        session.audio_buffer.clear()
                        session.vad_chunk_buffer.clear()
                        session.vad_iterator.reset_states()
                        session.agent_is_speaking = False
                    elif action == "unmute":
                        session.is_muted = False
                        session.vad_iterator.reset_states()
                        
                elif "text" in msg:
                    logger.debug(f"📩 Received chat message: {msg['text']}")
                    session.current_turn_id += 1
                    asyncio.create_task(session.run_llm_and_tts(
                        msg["text"], 
                        turn_id=session.current_turn_id
                    ))
                    
                if msg.get("type") == "grant_permission":
                    tool_id = msg.get("tool_id")
                    decision = msg.get("decision")  # "Allow Once", "Always Allow", "Deny"
                    logger.info(f"🛡️ Received capability decision: {tool_id} -> {decision}")
                    from core.capabilities import registry as cap_registry
                    from core.database import db
                    
                    if decision == "Allow Once":
                        cap_registry.grant_session_permission("default_user", tool_id, "Allow Session")
                    elif decision == "Deny":
                        # If they deny once, we might store it in session or db
                        cap_registry.grant_session_permission("default_user", tool_id, "Deny")
                    elif decision == "Always Allow":
                        await db.set_user_permission("default_user", tool_id, "Always Allow")
                        
                    # Tell user they can try again
                    confirm_text = "Permission updated. Please repeat your request."
                    await session.safe_send_json({"type": "agent_message", "text": confirm_text, "is_final": True})
                    await session.enqueue_tts(confirm_text, turn_id=session.current_turn_id)
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected cleanly")
    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}", exc_info=True)
    finally:
        await session.stop()
        if session.gemini_manager:
            await session.gemini_manager.close()
        logger.info("🔌 Session cleaned up")

@ws_router.websocket("/ws/gemini-live")
async def gemini_live_websocket_endpoint(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id", "")
    logger.info(f"🔌 Incoming Gemini Live WS from {websocket.client}")
    await websocket.accept()
    
    if session_id and session_id in gs.active_sessions:
        old_session = gs.active_sessions[session_id]
        old_session.is_connected = False
        
    session = VoiceSession(websocket, engine="gemini_live", session_id=session_id)
    if session_id:
        gs.active_sessions[session_id] = session

    try:
        try:
            await session.connect_gemini()
            # Inform frontend which engine is active
            await session.safe_send_json({"type": "engine_mode", "mode": "gemini_live"})
        except Exception as e:
            logger.error(f"❌ Gemini Live connection failed: {e}. Falling back to local pipeline.")
            session.engine = "nexus"  # Graceful failover, don't disconnect client
            await session.safe_send_json({"type": "engine_mode", "mode": "groq"})

        # Same loop as /ws/nexus
        while session.is_connected:
            try:
                data = await websocket.receive()
            except (WebSocketDisconnect, RuntimeError):
                break
            
            if "disconnect" in data:
                break
            elif "bytes" in data and data["bytes"] is not None:
                if session.engine == "gemini_live" and session.gemini_manager and session.gemini_manager.is_connected:
                    try:
                        await session.gemini_manager.send_audio(data["bytes"])
                    except Exception as e:
                        logger.error(f"❌ Failed to send audio to Gemini Live: {e}")
                else:
                    try:
                        await session.process_audio(data["bytes"]) # Failover path
                    except Exception as e:
                        logger.error(f"❌ Failed to process local audio: {e}")
            elif "text" in data and data["text"] is not None:
                msg = json.loads(data["text"])
                if msg.get("type") == "vision_frame":
                    if session.gemini_manager and session.gemini_manager.is_connected:
                        await session.gemini_manager.send_video_frame(msg.get("data"))
                    continue
                if msg.get("type") == "ping":
                    await session.safe_send_json({"type": "pong", "timestamp": msg.get("timestamp")})
                    continue
                if msg.get("type") == "vad_stop":
                    if session.engine == "gemini_live" and session.gemini_manager and session.gemini_manager.is_connected:
                        await session.gemini_manager.send_turn_complete()
                    continue
                if msg.get("type") == "audio_finished":
                    session.agent_is_speaking = False
                    if session.state == SessionState.SPEAKING:
                        session._change_state(SessionState.IDLE)
                        session.post_tts_guard_until = time.time() + 1.2
                    continue
                if msg.get("type") == "settings":
                    session.selected_persona = msg.get("persona") or "female"
                    session.selected_provider = msg.get("ttsProvider") or "edge"
                    session.selected_language = msg.get("language") or "auto"
                    continue
                if "text" in msg:
                    txt = msg["text"].lower().strip()
                    is_action = False
                    # Action keywords + common typos like "opem"
                    action_kws = getattr(session, "_ACTION_KEYWORDS", ("open ", "launch ", "start ", "run ", "close ", "kill ", "quit ", "screenshot", "type ", "press ", "click "))
                    if any(txt.startswith(kw) for kw in action_kws) or txt.startswith("opem "):
                        is_action = True

                    if session.engine == "gemini_live" and session.gemini_manager and session.gemini_manager.is_connected and not is_action:
                        await session.gemini_manager.send_text(msg["text"], turn_complete=True)
                    else:
                        session.current_turn_id += 1
                        asyncio.create_task(session.run_llm_and_tts(msg["text"], turn_id=session.current_turn_id))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"❌ WS Error: {e}", exc_info=True)
    finally:
        try:
            await websocket.send_json({"type": "log", "level": "warn", "message": "WebSocket disconnected"})
        except Exception:
            pass
        await session.stop()
        if session.gemini_manager:
            await session.gemini_manager.close()



