# Nexus Feature Roadmap

To ensure Nexus is built robustly without becoming a "science project", we will execute feature implementation in this strict chronological order. No step can begin until the previous step has 100% test coverage and is fundamentally stable.

## 1. Reliable Voice Input/Output
* **Goal**: Flawless, crash-free two-way streaming.
* **Scope**: Stabilize `useNexusVoice.ts`, the WebSocket Gateway, Groq STT, and Gemini TTS. Ensure the VAD never locks up.

## 2. Robust Sentence Cleanup and Filler Removal
* **Goal**: Ensure the user sounds intelligent and concise.
* **Scope**: Implement the fast LLM-based `SpeechCleaner` node between the STT output and the main LLM. Strip all "ums", "uhs", and self-corrections.

## 3. Voice State UI Integration
* **Goal**: Total user transparency regarding the AI's internal state.
* **Scope**: Build clean, modern React components reacting to `Listening`, `Thinking`, `Speaking`, `Working`, and `Error` WebSocket events.

## 4. Browser Automation
* **Goal**: Execute repetitive web tasks via voice.
* **Scope**: Integrate an MCP-compliant Browser Tool (e.g., using Playwright) that handles form filling and web scraping securely.

## 5. Desktop Automation (The Companion Daemon)
* **Goal**: IRIS-style local OS manipulation.
* **Scope**: Create a standalone Node/Electron daemon that listens for MCP commands from the cloud brain to execute repetitive window tasks and coordinate clicks.

## 6. Persistent Retrievable Memory
* **Goal**: Cross-session continuity.
* **Scope**: Implement SQLite (FTS5) and local markdown storage (Hermes pattern) to persist user profiles and historical context.

## 7. Safe Tool Execution
* **Goal**: Prevent random spaghetti code when tools are added.
* **Scope**: Formalize the Model Context Protocol (MCP) in the Python backend. Ensure action logging, explicit permission boundaries, and failure recovery.

## 8. Non-Brittle Agent Routing
* **Goal**: Delegate complex tasks seamlessly.
* **Scope**: Implement Hermes's `batch_runner.py` pattern to spawn isolated sub-agents for long-running workflows without blocking the primary voice loop.

## 9. Multi-Model Routing
* **Goal**: Optimize cost and intelligence.
* **Scope**: Introduce logic to route to Claude 3.5 Sonnet for deep coding, Llama-3-8b for basic speech cleanup, and Gemini 2.5 Flash for rapid conversation.
