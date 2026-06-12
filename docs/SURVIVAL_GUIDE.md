# Nexus AI: 14,400 Minute Survival & Deployment Guide

To handle **14,400 minutes per month** (roughly 8 hours of audio a day), we are moving from a "cloud-only" hobbyist setup to a **Local-First Hybrid Stack**. This ensures Rs 0 cost for STT/TTS and bypasses cloud API rate limits.

## 🚀 The "Heavy-Duty" Architecture

| Component | Technology | Role | Cost |
| :--- | :--- | :--- | :--- |
| **STT** | `faster-whisper` (Large-v3) | Always-on local transcription | Rs 0 |
| **TTS** | `Kokoro-82M` (ONNX) | Instant local speech generation | Rs 0 |
| **LLM** | Groq (Llama 3.3 70B) | High-speed intelligent processing | Free Tier |
| **Tunnel** | `ngrok` / `Cloudflare Tunnel` | Expose local STT/TTS to Vercel | Rs 0 |
| **Persistence** | Supabase / Firestore | Cloud memory for context sync | Rs 0 |

---

## 🛠️ Implementation Steps

### 1. Local Worker Setup (`backend/scripts/local_worker.py`)
We will create a high-performance local worker that runs on your NVIDIA GPU (STT) and CPU (TTS).
- **STT:** `faster-whisper` will run a local WebSocket server to receive audio chunks.
- **TTS:** `kokoro-onnx` will provide a FastAPI endpoint for text-to-audio conversion.

### 2. The API Bridge
To connect your **Vercel Frontend** to your **Local Hardware**:
1. Run `ngrok http 8000` on your machine.
2. Update the frontend `NEXT_PUBLIC_LOCAL_VOICE_URL` with the ngrok address.
3. Frontend calls local machine for "Heavy" audio processing.

### 3. Durability Tweaks (The "Survival" Part)
- **VAD Gate:** We will implement a Voice Activity Detection gate in the frontend to stop streaming silence, saving 90% of processing overhead.
- **Context Summarization:** To survive 30 days of 8-hour sessions, the `MemoryService` will automatically summarize conversations after every 10,000 tokens to keep the LLM context lean and fast.

---

## 💻 Hardware Status (CONFIRMED)
- **Detected GPU:** NVIDIA GeForce RTX 3050 Laptop GPU
- **VRAM:** 4GB
- **Status:** **CAPABLE** with `int8` quantization.
- **Optimization:** Using `faster-whisper` Medium model + `int8` to ensure it fits in 4GB while maintaining high accuracy.

---

## 🛠️ What We Need To Do (Action Plan)

### Phase 1: Local Environment Setup
1. **Install Dependencies:**
   ```powershell
   pip install -r backend/requirements_local.txt
   ```
2. **Download Local Models:**
   - Place `kokoro-v0_19.onnx` and `voices.json` in `backend/src/backend/voice/models/`.
   - Faster-Whisper will auto-download on first run.

### Phase 2: Start the Engine
1. **Launch Worker:**
   ```powershell
   python backend/src/backend/voice/local_worker.py
   ```
2. **Bridge to Cloud:**
   ```powershell
   ngrok http 8000
   ```

### Phase 3: Integration
1. **Frontend Update:** Update `NexusContext.tsx` to detect `isLocal` mode and route audio to the local worker URL.
2. **Persistence Loop:** Ensure `MemoryService` in the backend continues to sync local transcripts to Firestore/Supabase for cloud-ready memory.

---

## Next Steps
- [x] Create `backend/requirements_local.txt`.
- [x] Create `backend/src/backend/voice/local_worker.py`.
- [ ] Install local dependencies and download Kokoro models.
- [ ] Implement VAD gate in `NexusContext.tsx`.
