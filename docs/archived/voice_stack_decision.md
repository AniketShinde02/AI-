# Voice Stack Decision: GetStream Video + Vision Agents

## Context
Nexus 2.0 requires a robust, low-latency, and cost-effective voice interaction pipeline. The system needs to handle streaming audio, perform Speech-to-Text (STT), orchestrate LLM reasoning, and provide Text-to-Speech (TTS) playback with interruption support.

## Decision
We have selected **GetStream Video** combined with the **Vision Agents** framework (GetStream's specialized SDK for AI agents) and **Deepgram** for STT.

## Rationales

### 1. Low-Latency Orchestration
GetStream's Vision Agents SDK is specifically built for "Realtime AI Agents". It handles the complex WebRTC signaling, audio jitter buffers, and VAD (Voice Activity Detection) natively. This allows the backend to focus on tool execution and conversation logic rather than raw audio byte processing.

### 2. Built-in Interruption Handling
Interruption is the "hardest" part of voice assistants. Vision Agents provides native support for detecting when a user starts speaking while the assistant is talking, automatically silencing the assistant and resetting the turn.

### 3. Cost Efficiency (Free Tier Strategy)
- **GetStream Video**: Offers ~333,000 participant-minutes/month for free, plus a $100 monthly credit on the Pro tier for startups. For a solo developer or small beta, this is effectively **$0 infrastructure cost**.
- **Deepgram**: Integrated via the Vision Agents STT plugin. Deepgram offers $200 in free credits and is significantly cheaper and faster than Google/AWS STT.

### 4. Developer Experience
GetStream provides first-class SDKs for both our backend (Python) and frontend (React/Next.js), including pre-built hooks and components for "Audio Rooms" which map perfectly to our assistant sessions.

## Integration Plan

### Phase 1: Backend Setup (Python)
1.  **Dependencies**: `getstream`, `vision-agents`, `vision-agents-plugins-getstream`.
2.  **Service**: Implement `services/stream_client.py` to handle `audio_room` creation and token generation.
3.  **Agent**: Implement `core/voice.py` using `VisionAgent` to register callbacks for transcription events and tool calls.

### Phase 2: Frontend Setup (Next.js)
1.  **Dependencies**: `@stream-io/video-react-sdk`.
2.  **Hook**: Create `hooks/useVoiceSession.ts` to manage joining/leaving calls and tracking call state.
3.  **UI**: Implement a `VoiceButton` and `AudioVisualizer` component using the Stream SDK primitives.

### Phase 3: Latency Optimization
1.  **Region Locking**: Ensure Stream calls are pinned to the nearest edge location (e.g., `us-east-1` or `eu-west-1`).
2.  **Streaming TTS**: Use `audio/pcm` or `audio/opus` streaming to start playback before the entire TTS buffer is generated.

## Alternatives Considered
- **LiveKit + Soniox**: Highly capable but requires managing (or paying for) a LiveKit server/cloud. Documentation for AI-specific agents is less integrated than GetStream's Vision Agents for our specific Next.js/Python stack.
- **OpenAI Realtime API (Raw)**: Extremely expensive ($0.06/min). We prefer using a standard LLM (GPT-4o-mini / Groq) over a WebRTC bridge to keep costs under control.
