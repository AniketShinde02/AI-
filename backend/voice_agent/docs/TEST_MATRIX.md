# Nexus Fail-Safe Test Matrix

| Component | Scenario | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|---|
| **Audio Processing** | Send empty 0-byte PCM chunk | Frontend ignores buffer creation, no crashes. | Ignored properly, no crash. | **PASS** |
| **Audio Processing** | Rapidly toggle mic mute/unmute | Buffer is cleared and state reset, no memory leak. | VAD buffer resets on toggle. | **PASS** |
| **LLM Inference** | Empty transcript sent to LLM | Rejected by STT hallucination/noise filter before LLM. | STT drops empty/noise strings. | **PASS** |
| **TTS Generation** | Gemini 429 Rate Limit | Exponential backoff retry triggered instead of crashing. | Retries properly implemented. | **PASS** |
| **TTS Generation** | Change Voice Settings mid-call | Next turn uses the newly selected voice automatically. | `voice_name` updates per turn. | **PASS** |
| **WebSocket** | Network disconnect | Disconnects cleanly, reconnects with fresh session on page refresh. | State cleans up correctly. | **PASS** |
| **WebSocket** | Frontend refresh mid-speech | Backend catches WebSocketDisconnect and cancels tasks. | Handled gracefully. | **PASS** |

## Manual Test Instructions
1. **Empty Audio:** Modify client to send 0 bytes. Check console.
2. **Mic Toggle:** Spam the mic button 20 times. Ensure browser memory remains stable.
3. **Voice Change:** Open settings, change to "Professional Male", speak immediately. Verify tone change.
