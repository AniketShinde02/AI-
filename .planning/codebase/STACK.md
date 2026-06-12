# Project Stack

## Frontend
- **Framework**: Next.js 15+ (App Router)
- **Styling**: Tailwind CSS, Lucide React (Icons)
- **State Management**: React Context (NexusContext)
- **API Client**: tRPC (Awesome-tRPC integration pending)
- **Animations**: CSS Transitions, Framer Motion (Glassmorphic effects)

## Backend (Voice Agent)
- **Framework**: FastAPI (Python 3.13)
- **Orchestration**: `vision-agents`
- **Providers**:
  - LLM: Groq (llama-3.3-70b-versatile, llama-3.1-8b-instant)
  - STT: Deepgram
  - TTS: ElevenLabs
  - WebRTC: GetStream
- **Environment**: Virtual Environment (venv)

## Tooling
- **Deployment**: Vercel (Frontend), Python Serve (Backend)
- **Code Mapping**: Graphify MCP
- **Automation**: PowerShell Control Script (run.ps1)
