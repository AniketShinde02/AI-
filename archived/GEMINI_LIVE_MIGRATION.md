# GEMINI_LIVE_MIGRATION.md
## Gap Analysis: Experimental to Production (Mode A)

The experimental implementation in `d:\AI\backend\voice_agent\experimental\gemini_live_voice.py` proves the Gemini Live bidirectional WebSocket architecture is viable and capable of sub-1s TTFA. However, it is not production-ready.

Below are the 5 critical missing pieces required before it can become the primary "Mode A" in `ws_main.py`.

### 1. Reconnection & Failover (Rate Limit Resilience)
- **Current State:** The `async with client.aio.live.connect()` block fails fatally on `WebSocketDisconnect` or `google.genai.errors.APIError` (e.g., HTTP 429).
- **Required Fix:** 
  - Wrap the connection in an exponential backoff retry loop.
  - If Gemini Live rate-limits, gracefully fallback to Mode B (Groq STT -> Groq LLM -> Edge TTS) within the same WebSocket session without dropping the client connection.

### 2. Interruption & Barge-in
- **Current State:** Audio chunks flow continuously from the client, but there is no explicit cancellation signal sent to Gemini when the user interrupts the AI.
- **Required Fix:** 
  - Integrate a VAD gate to detect user speech *while* the AI is speaking.
  - When barge-in is detected, send an interrupt signal via `session.send(clientContent=...)` or close the ongoing turn to halt Gemini's audio generation, saving tokens and stopping overlapping audio.

### 3. Memory & Context Injection
- **Current State:** The experimental session is completely stateless. It starts with a hardcoded greeting trigger and has no access to previous conversation history.
- **Required Fix:** 
  - At the start of the Live session, inject the rolling 8-turn `conversation_history` from `ws_main.py`.
  - Maintain a unified memory deque so switching between Mode A (Gemini Live) and Mode B (Groq) retains the conversation.

### 4. Tool Calling & Agent Integration
- **Current State:** The `config` object only specifies `response_modalities` and `system_instruction`. No tools are provided.
- **Required Fix:** 
  - Register the Nexus tool schema (`get_weather`, `ingest_codebase`, `consult_oracle`, etc.) in the `tools` configuration parameter.
  - Intercept `tool_call` events in the `receive_from_gemini` loop, execute the local Python functions, and send the `tool_response` back to the live session.

### 5. Prompt Synchronization
- **Current State:** Uses a hardcoded 5-line `SYSTEM_INSTRUCTION` completely divorced from the rich personality defined in `prompts.py`.
- **Required Fix:** 
  - Import `get_nexus_system_prompt()` and pass it to the `system_instruction` config.
  - Add specific phonetic instructions to enforce the Indian English accent natively, since Gemini Live does not have an explicit `en-IN` voice selector.

---

### Migration Strategy
Do **not** merge `gemini_live_voice.py` into `ws_main.py` yet.
Instead, build a standalone `GeminiLiveSessionManager` class that encapsulates the bidirectional stream and exposes a standard interface to `ws_main.py`. This ensures Mode A and Mode B remain decoupled and can failover cleanly.
