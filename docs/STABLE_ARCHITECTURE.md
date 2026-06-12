# STABLE ARCHITECTURE SNAPSHOT

## 1. Current Voice Flow
- The system uses the **Gemini Multimodal Live API** via WebSockets (`useGeminiLive.ts`).
- **Speech-to-Speech:** Gemini natively handles listening (STT), reasoning, and speaking (TTS) in one continuous stream without relying on intermediary models for the core loop.
- **Latency:** Extremely low due to the lack of external STT/TTS chaining.

## 2. Current WebSocket Flow
- **Frontend (`useNexusVoice.ts`):** Establishes a WebSocket connection to the Python backend on `ws://localhost:8000/ws`.
- **Backend (`ws_main.py`):** Handles incoming client connections, manages background tasks like `metrics_worker` for real-time telemetry (CPU, Memory via `psutil`), and proxies tool execution requests.

## 3. Current Gemini Live Setup
- Configuration is loaded via `@google/genai` or native WebSocket endpoints using the `gemini-2.5-flash` or `gemini-2.0-flash-exp` models.
- Voice response streams are decoded from base64 PCM and played through the Web Audio API (`AudioContext`).

## 4. Current RAG Setup
- The RAG Oracle is integrated as a tool definition within the Gemini Live setup.
- When Gemini determines a query requires deep knowledge or external document retrieval, it fires a `tool_call` to the backend.
- The backend queries a vector database (e.g., Supabase pgvector or Chroma) and returns the context.

## 5. Current Tool System
- **Tool Definitions:** Passed in the initial setup message to the Gemini API.
- **Execution Loop:**
  - Gemini emits a `toolCall`.
  - Frontend intercepts and either handles it locally (e.g., `change_theme`) or routes it to the backend via the standard WebSocket.
  - Backend executes the Python function.
  - Frontend sends the `toolResponse` back to the Gemini Live session so it can synthesize an audio reply.
