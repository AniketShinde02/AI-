# Technical Concerns & Roadmap

## Active Concerns
1. **Environment Dependency**: Backend requires `python.exe` from the specific `venv` path. Global execution fails. (Mitigated by `run.ps1`).
2. **Streaming Latency**: Groq streaming must maintain `is_first` token flags accurately for the voice agent to respond immediately.
3. **Port Conflicts**: Port 8000 and 3000 are frequently blocked by orphaned processes on Windows.

## Roadmap
1. **tRPC Refactor**: Implement the "Awesome-tRPC" patterns for better API documentation.
2. **Multi-Model Support**: Fully wire the model toggle in the UI to the backend session launcher.
3. **Persistent Memory**: Integrate a vector database for long-term agent memory.
