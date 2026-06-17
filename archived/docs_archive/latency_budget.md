# Latency Budget: The "Magical Experience" Bar

## 1. The 1-Second Rule
For a voice assistant to feel natural, the "Total Turn-Around Time" (TTAT) from user silence to assistant speech must be **< 1.0 seconds (P95)**.

## 2. Latency Breakdown (Target P95)

| Component | Provider | Target Latency | Optimization |
| :--- | :--- | :--- | :--- |
| **STT (Transcription)** | Deepgram | **200ms** | WebSocket streaming, small models. |
| **Intent Classification** | Groq (Llama 3) | **150ms** | Minimal prompt, high-throughput provider. |
| **LLM Reasoning** | GPT-4o-mini | **400ms** | Streaming tokens, partial output execution. |
| **TTS (Generation)** | ElevenLabs | **200ms** | PCM streaming, Turbo v2.5 model. |
| **Transport / RTC** | GetStream | **50ms** | Edge-optimized signaling. |
| **TOTAL** | -- | **1000ms** | -- |

## 3. Optimization Techniques

### 1. Speculative Execution
- Start the Intent Classifier the moment Deepgram emits an `interim` result with high confidence.
- Don't wait for the `final` transcript if the interim is already clear.

### 2. Stream-to-Stream Pipeline
- **Input**: User Audio → Deepgram WebSocket.
- **Middle**: Text Fragment → LLM Streaming.
- **Output**: LLM First Token → ElevenLabs Streaming.
- **Result**: Audio starts playing while the LLM is still "thinking" about the end of the sentence.

### 3. Tool Pre-computation
- If the user asks for Gmail, start the browser session in the background *while* the assistant is saying "Sure, checking your emails...".

## 4. Monitoring
- We will track `ttat_ms` as a custom metric in Sentry/Grafana.
- Any turn exceeding 2.5 seconds is considered a "Failure" and triggers an optimization review.
