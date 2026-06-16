# Nexus Power of 3 Architecture

This document synthesizes the strongest elements of IRIS, Hermes, and Stonic into a clean, modern architecture for Nexus. 

## The Philosophy: No Monoliths, No Spaghetti
Nexus will be divided into strictly isolated layers. The Frontend (Stonic-style wrapper) handles purely UI and audio capture. The Backend (Hermes-style headless core) handles intelligence and tool execution. External Daemons (IRIS-style native control) handle OS-level automation.

## Layer 1: The UI Wrapper (Inspired by Stonic)
* **Responsibility**: Render chat, render Voice State UI (Listening/Thinking/Speaking), and capture raw microphone input.
* **Architecture**: Next.js 15 App Router.
* **Rule**: Absolutely no heavy logic, no direct DB calls, and no API keys stored in the frontend. It is a dumb, beautiful terminal.

## Layer 2: The Headless Brain (Inspired by Hermes)
* **Responsibility**: Manage the Agent Loop, route LLM calls, handle WebSocket connections, and maintain conversational state.
* **Architecture**: Pure Python 3.11 with FastAPI. Managed exclusively via `uv`. 
* **Key Components**:
  * `Gateway`: The WebSocket handler (`ws_main.py` refactored into smaller sub-routers).
  * `Agent Loop`: The state machine evaluating if the user is speaking, if a tool should be called, or if text should be synthesized.
  * `Memory`: Local SQLite database (FTS5) combined with Markdown files for long-term user context.

## Layer 3: Tool & Automation Registry (Inspired by Hermes & IRIS)
* **Responsibility**: Execute OS, browser, and web actions safely.
* **Architecture**: Model Context Protocol (MCP) servers.
* **Key Components**:
  * **Browser Tasks**: A dedicated MCP server utilizing Playwright to handle repetitive web workflows safely.
  * **Native Automation**: An optional "Nexus Companion Daemon" (learning from IRIS's Telekinesis) running locally on the user's OS to perform direct coordinate clicking and window management.

## The Data Flow
1. **Voice Input** -> Next.js captures Base64 PCM -> WebSocket -> Python Gateway.
2. **STT & Speech Cleanup** -> Groq Whisper -> Python Text Normalizer.
3. **Agent Loop** -> LLM evaluates text -> Decides to Reply or Execute Tool.
4. **Tool Execution** -> Python Backend routes request to MCP Server -> MCP Server controls Browser/OS -> Returns state.
5. **Voice Output** -> Gemini TTS -> Python Gateway -> WebSocket -> Next.js AudioContext.
