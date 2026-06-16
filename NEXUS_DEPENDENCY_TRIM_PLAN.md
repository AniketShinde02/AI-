# Nexus Dependency Trim Plan

This document outlines the strict removal of dead, heavy, and unused dependencies from the Python backend (`requirements.txt`).

## 1. Dead TTS & STT Packages
* **`kokoro-onnx`**
  * *Usage*: None in production. Abandoned local TTS experiment.
  * *Action*: **REMOVE**. Saves ~2GB of model weights and heavy ONNX runtime overhead.
* **`faster-whisper`**
  * *Usage*: None in production. Abandoned local STT fallback.
  * *Action*: **REMOVE**. Saves significant RAM/VRAM. We rely entirely on Groq Whisper API.
* **`deepgram-sdk`**
  * *Usage*: Superseded by Groq STT.
  * *Action*: **REMOVE**.
* **`elevenlabs`**
  * *Usage*: Superseded by Gemini TTS.
  * *Action*: **REMOVE**.

## 2. Experimental / Bloated Packages
* **`vision-agents` & `vision-agents-plugins-*`**
  * *Usage*: Experimental computer vision agents not wired into the main WebSocket audio loop.
  * *Action*: **REMOVE** from core production requirements. If needed later, move to a separate standalone microservice.
* **`getstream` & `stream-chat`**
  * *Usage*: Stream SDKs. Currently, pure WebSockets handle audio directly.
  * *Action*: **REMOVE** unless strictly necessary for chat persistence.
* **`aiortc`**
  * *Usage*: WebRTC library. The architecture successfully pivoted to pure WebSocket Base64 PCM.
  * *Action*: **REMOVE**.

## 3. Verification Protocol
Before executing `pip uninstall`, confirm removal safety via:
1. `grep -rn "import kokoro_onnx" .` -> Verify 0 hits in active `src/` or `ws_main.py`.
2. `grep -rn "vision_agents" .` -> Verify 0 hits in active pipeline.
3. Check `requirements_local.txt` and delete the file entirely, merging any valid local needs into `pyproject.toml` managed by `uv`.
