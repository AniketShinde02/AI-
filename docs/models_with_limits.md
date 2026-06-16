# AI Provider Models & Rate Limits

## Groq API (Inference Engine)

Groq provides ultra-fast inference using Language Processing Units (LPUs). In this ecosystem, Groq is used primarily for **Speech-to-Text (Whisper)** and **Reasoning (LLMs)** where sub-second latency is required.

### Supported Models for Scalable Deployment
*Only highly scalable, production-ready models are included below.*

| Model Name | Context Window | Use Case |
|---|---|---|
| `llama3-8b-8192` | 8,192 tokens | Fast conversational logic, routing, short-form tasks |
| `llama3-70b-8192` | 8,192 tokens | Complex reasoning, deep research, coding |
| `mixtral-8x7b-32768` | 32,768 tokens | High-context RAG, long document analysis |
| `gemma-7b-it` | 8,192 tokens | Lightweight instruct tasks |
| `whisper-large-v3` | 25 MB max size | Ultra-fast Audio Transcription (STT) |

### Groq Rate Limits (Standard On-Demand)
Groq limits are enforced at the Organization level. Hitting any of these limits will trigger a 429 error.

*   **Free Tier (Prototyping):**
    *   **RPM (Requests Per Minute):** 30
    *   **RPD (Requests Per Day):** 14,400
    *   **TPM (Tokens Per Minute):** 6,000 to 7,000 (varies by model)
    *   **TPD (Tokens Per Day):** 500,000

*   **Developer Tier (Paid/Pay-as-you-go):**
    *   Unlocks up to **10x** the rate limits of the Free Tier instantly upon adding a billing method.
    *   **TPM (Tokens Per Minute):** Scales significantly higher for production workloads.

---

## Gemini API (Voice & Vision Engine)

### Supported Models
| Model Name | Use Case |
|---|---|
| `gemini-1.5-flash-tts` | Real-time text-to-speech generation |
| `gemini-1.5-flash` | Multimodal input (Video/Vision), fast conversational AI |
| `gemini-1.5-pro` | Complex Multimodal tasks, massive context (up to 2M tokens) |

### Gemini Rate Limits (Free Tier)
*   **Gemini 1.5 Flash TTS:**
    *   **RPM:** 100
    *   **TPM:** 4,000,000 (shared)
    *   **RPD:** 1,500
*   **Gemini 1.5 Flash:**
    *   **RPM:** 15
    *   **TPM:** 1,000,000
    *   **RPD:** 1,500
*   **Gemini 1.5 Pro:**
    *   **RPM:** 2
    *   **TPM:** 32,000
    *   **RPD:** 50

### Gemini Rate Limits (Pay-As-You-Go / Tier 1+)
*Unlocks significantly higher limits by attaching a billing account.*
*   **Gemini 1.5 Flash TTS:** Scales beyond 100 RPM based on tier.
*   **Gemini 1.5 Flash:** 1,000 RPM, 4,000,000 TPM, Unlimited RPD.
*   **Gemini 1.5 Pro:** 360 RPM, 2,000,000 TPM, Unlimited RPD.

---

## How to Prevent Gemini 429 Rate Limits
In real-time voice applications, Gemini's strict 15 RPM free-tier limit is easily exhausted in a rapid conversation. To prevent catastrophic failure:

1.  **Immediate Async Failover (Implemented):** Do not use synchronous retries (which block the thread). Instead, instantly catch the `429 RESOURCE_EXHAUSTED` exception and switch to an unmetered/free fallback provider like **Edge TTS**.
2.  **Turn Accumulation:** Instead of sending every tiny sentence chunk to Gemini TTS independently, accumulate the full response paragraph before making the TTS API request. This reduces API calls by 3x - 5x per turn.
3.  **Upgrade Tier:** Switching to a Pay-as-you-go (Developer) tier on Google AI Studio removes the strict 15 RPM bottleneck, allowing unlimited RPM governed only by your billing quota.
