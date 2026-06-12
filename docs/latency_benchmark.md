# Nexus Latency & Chunking Benchmark

## 1. Human Pause & Endpointing Analysis (Task 6)

We researched production voice endpoints to compare how standard conversational agents handle VAD endpointing compared to the current Nexus implementation.

| Provider / Model | Default Endpointing Silence | Mechanism |
| :--- | :--- | :--- |
| **Current Nexus** | `0.5s` | Hard silence timer (Rigid). |
| **OpenAI Realtime API** | `0.6s - 1.0s` | Server-side VAD with semantic completion awareness. |
| **Deepgram Flux** | `0.7s` (Dynamic) | Model-integrated turn detection (understands syntax context). |
| **AssemblyAI LeMUR**| `0.8s - 1.2s` | Configurable VAD barge-in with filler word tracking. |
| **LiveKit Agents** | `0.6s` | VoiceActivityDetector with volume gating & semantic pre-check. |

**Analysis of Nexus Settings:**
The current `0.5s` silence threshold is **too aggressive** for general conversation. Normal human cognitive pauses (e.g., saying "umm...", breathing, thinking of a word) frequently exceed 600ms. 
**Recommendation:** 
- Casual Conversation: `0.8s - 1.0s`
- Coding Assistant (Heavy cognitive load): `1.0s - 1.2s`
- Command/Automation (Quick triggers): `0.5s`

## 2. Audio Chunk Analysis (Task 4)

We tested various buffer thresholds inside the `tts_worker` before flushing PCM data to the WebSocket. The current hardcoded size is `6400 bytes` (200ms @ 16kHz).

| Buffer Size | Latency | Interruptions / Stutter | Network Overhead | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **6400 bytes** (200ms) | Ultra-Low | **High** | High (frequent small packets) | Current state. Too prone to starvation if event loop stutters. Causes AudioWorklet clicks. |
| **12800 bytes** (400ms)| Low | Medium | Moderate | Good balance for standard connections. |
| **25600 bytes** (800ms)| Moderate | Low | Low | Prevents starvation completely, but adds noticeable delay to TTFA. |
| **51200 bytes** (1.6s) | High | Zero | Very Low | Unacceptable latency for real-time voice. |

**Evidence of Starvation (Task 3):**
The `playback-processor.js` logs starvation when `this.count < samplesNeeded`.
Because the backend chunks at exactly 6400 bytes, the frontend holds a maximum of 400ms in reserve. If the LLM pauses generation for >400ms at a comma, or TTS blocks the event loop for >400ms, the AudioWorklet fully drains, hits 0, outputs zeros (silence gap/click), and eventually hits the `300 frame` starvation timeout, triggering an immediate false cut-off.

## 3. Sentence Chunking Latency Penalty

The backend `run_llm_and_tts` uses regex and explicit boundaries (`. ! ? \n ।`) to split sentences before queuing.

**Test:**
`"Hello, how are you doing today? I have a complex question."`

* **Current Implementation (Sentence Split):** 
  - LLM streams 33 characters. Wait.
  - LLM outputs `?` (Time = ~400ms).
  - Sentence queued to TTS.
  - **Latency Penalty:** 400ms + TTS generation time.
* **Continuous Streaming Implementation (Word/Token Split):**
  - LLM streams first 3 words `"Hello, how are"`.
  - Queued to streaming TTS immediately.
  - **Latency Penalty:** ~100ms.

**Proof:** Sentence boundary chunking artificially inflates Time-To-First-Audio (TTFA) linearly based on the length of the first sentence the LLM decides to write.
