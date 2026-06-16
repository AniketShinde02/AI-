# STONIC_REUSE_MATRIX.md
## Stonic: Good Ideas vs Technical Debt

### What Stonic Is
Stonic is a commercial Electron app (Main-Electron-App) combined with a Next.js Agent-Town frontend. It uses Hermes as its embedded Python backend (the `python-embedded/` directory contains Hermes installed as a pip package). Stonic itself is a distribution wrapper around Hermes.

**Key Insight:** Stonic ≠ original code. Stonic is Hermes + Electron wrapper + a Next.js dashboard. The "Stonic brain" is Hermes.

---

### Good Ideas

| Pattern | Evidence | Value for Nexus |
|---------|----------|-----------------|
| Electron as Native Wrapper | `Main-Electron-App/` bundles a full Chromium with local Python backend | Useful only if Nexus ever ships as a desktop app. Not needed now. |
| Embedded Python Distribution | `python-embedded/` ships Python 3.x with all dependencies pre-installed | Valuable for one-click local distribution. Note for future. |
| Wake Word in Background | `wake_word_bg.py` implements always-on wake-word detection | Directly useful: Nexus could add a `nexus_wake_word.py` that triggers voice mode hands-free. |
| Agent-Town Dashboard | `Agent-Town/` is a Next.js dashboard for managing agents | Nexus already has a superior UI (`frontend/`). Not needed. |

### Technical Debt to Avoid

| Pattern | Why It's Debt |
|---------|--------------|
| Bundling Python inside Electron | Creates massive binary (200MB+). Nexus's cloud architecture avoids this entirely. |
| Stonic's audio pass-through | Stonic calls the Hermes REST API from Electron → Next.js → Python. Triple hop latency. |
| No real voice streaming | Stonic's voice is Hermes voice (file-upload STT). Not real-time. |
| Single-provider LLM | Stonic uses OpenAI only, no fallback. |

---

### Net Verdict
**Copy from Stonic:** Only the `wake_word_bg.py` concept (if hands-free activation is desired later).  
**Reject from Stonic:** Everything else. Nexus's web-first architecture is already superior.
