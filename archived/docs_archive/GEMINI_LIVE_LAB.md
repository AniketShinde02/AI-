# GEMINI LIVE LAB - Experimental Engine

## Implementation Details
We implemented a backend relay script (`backend/experimental/gemini_live_voice.py`) to stream raw PCM audio bidirectionally between the Frontend mic and the Gemini Live WebSocket API (`client.aio.live.connect`).

The frontend Settings UI has a new **Voice Engine** dropdown allowing you to switch between `Standard` and `Gemini Live Experimental`. When toggled to Experimental, the frontend connects to `/ws/gemini-live` instead of the production `/ws/nexus` socket.

### Data Flow
`Mic` → `Frontend (Float32)` → `Backend Relay (/ws/gemini-live)` → `Gemini Live (Int16)` → `Backend Relay` → `Frontend (Float32)` → `Speaker`

---

## Lab Metrics
*(Fill these out during microphone testing)*

- **Response Latency:** [__] ms
- **Interruption Latency:** [__] ms
- **Audio Quality:** [__]
- **Voice Quality:** [__]
- **Reliability:** [__]
- **Reconnect Behavior:** [__]

---

## Persona Validation
*(Test the following with your microphone)*

- **Nexus identity:** [Maintained / Lost]
- **Hinglish Support:** [Excellent / Poor]
- **Humor & Sarcasm:** [Present / Absent]
- **Short Answers:** [Maintained / Hallucinated LLM Fillers]

---

## Recommendation

**Recommendation: [A. Keep Standard / B. Hybrid / C. Full Migration]**

*Preliminary note before tests:* Based on text-to-audio tests, **A. Keep Standard** is the recommended choice. The Gemini Live API acts as a complex reasoning agent. Using it purely as a voice engine often results in conversational drift unless heavily prompted. Standard Groq + Dedicated TTS remains the fastest, most predictable architecture.
