# Nexus Architecture - 2026-04-27

## System Overview
Nexus is a production-grade AI platform featuring real-time streaming voice interactions and a unified chat interface.

## Core Components
1. **Frontend (Next.js 15)**
   - **NexusContext**: Central state management for voice/chat sessions.
   - **tRPC**: Type-safe communication with the Next.js API.
   - **GetStream SDK**: WebRTC transport for real-time voice.
   - **InputArea**: Unified interaction surface with dynamic model selection.

2. **Next.js API (tRPC)**
   - **getVoiceSession**: Orchestrates Stream call creation and triggers the Python Agent.
   - **chat**: Direct Groq API integration for text-mode inference.

3. **Python Voice Agent (Vision-Agents)**
   - **main.py**: Production Runner using `AgentLauncher`.
   - **GroqLLM**: Custom streaming LLM provider (llama-3.3-70b).
   - **Deepgram STT**: Sub-second speech-to-text.
   - **ElevenLabs TTS**: High-fidelity multilingual voice synthesis.

## Data Flow (Voice)
`User Mic` -> `Stream WebRTC (Edge)` -> `Deepgram (STT)` -> `Groq (LLM)` -> `ElevenLabs (TTS)` -> `Stream WebRTC` -> `User Speaker`

## Knowledge Graph Status
- **Files Mapped**: `main.py`, `llm.py`, `router.ts`, `InputArea.tsx`, `NexusContext.tsx`.
- **Primary Abstractions**: `AgentLauncher`, `EdgeTransport`, `NexusContext`, `tRPC Router`.
