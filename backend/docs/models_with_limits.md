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

---

## Cerebras AI (Fast Inference Engine)

Cerebras provides ultra-fast inference using its custom wafer-scale engines.

### Supported Models
| Model Name | Max Context Length | Status |
|---|---|---|
| `gpt-oss-120b` | 131,000 tokens | Production |
| `zai-glm-4.7` | 131,072 tokens | Preview |

### Cerebras Rate Limits (Organization Level)
*Limits are enforced on both Requests and Tokens across different time intervals.*

*   **gpt-oss-120b:**
    *   **Requests:**
        *   1,000 RPM (Requests Per Minute)
        *   60,000 RPH (Requests Per Hour)
        *   1,440,000 RPD (Requests Per Day)
    *   **Tokens:**
        *   1,000,000 TPM (Tokens Per Minute)
        *   120,000,000 TPH (Tokens Per Hour)
        *   2,000,000,000 TPD (Tokens Per Day)

*   **zai-glm-4.7:**
    *   **Requests:**
        *   500 RPM (Requests Per Minute)
        *   30,000 RPH (Requests Per Hour)
        *   720,000 RPD (Requests Per Day)
    *   **Tokens:**
        *   500,000 TPM (Tokens Per Minute)
        *   30,000,000 TPH (Tokens Per Hour)
        *   720,000,000 TPD (Tokens Per Day)

*Note: You may experience rate limits over shorter time intervals. For example, a rate limit of 60 requests per minute (RPM) may be enforced as 1 request per second.*

---

## Other LLM Providers

### DeepSeek API
*   **Free Tier / Trial:** Subject to dynamic rate limiting based on server load.
*   **Typical RPM:** 10 to 30 Requests Per Minute (RPM) during typical usage.
*   **Notes:** No fixed hard limit. Often throttles or returns 429 errors during high traffic. Shared infrastructure.

### Mistral API
*   **Free Tier (Evaluation/Prototyping):** Highly restrictive.
*   **Global Rate Limit:** 1 Request Per Second (RPS) (approx 60 RPM).
*   **Metrics Enforced:** RPS, Tokens Per Minute (TPM), and Tokens Per Month.
*   **Notes:** Automatically upgrades limits when moving to Scale plan (pay-as-you-go).

### Mistral Cloud API
*   **Free Tier:** No payment method linked.
    *   **Tokens Per Day (TPD):** 200,000
*   **Developer Tier (Requires linked payment method):**
    *   **Tokens Per Day:** 20,000,000
    *   **RPM/RPD:** Meta-Llama-3.3-70B-Instruct allows 240 RPM / 48,000 RPD.

### OpenRouter API
*   **Standard Free Tier (No credits history):**
    *   **Requests Per Day:** 50
    *   **Requests Per Minute:** 20
*   **With Lifetime Credits (>$10):**
    *   **Requests Per Day:** 1,000
    *   **Requests Per Minute:** 20
*   **Notes:** Applies to free models. Paid models are subject to upstream provider limits.

### Hugging Face Inference API
*   **Free Tier:**
    *   **Requests Per Day:** ~1,000 (500 for anonymous users).
    *   **Payload Limit:** ~2 MB HTTP body size.

---

## Audio & Voice Services

### ElevenLabs API (TTS)
*   **Free Tier:**
    *   **Monthly Credits:** 10,000 characters per month.
    *   **Concurrency limits:** Strict concurrency limits, returns 429 Too Many Requests if concurrency is too high.

### Cartesia API (TTS/STT)
*   **Free Tier:**
    *   **Monthly Credits:** 20,000 model credits (approx 20,000 chars) + $1 of voice agent usage.
    *   **Concurrency (Sonic TTS):** 2 simultaneous requests.
    *   **Concurrency (Ink STT):** 8 simultaneous requests.

### Deepgram API (STT)
*   **Free Tier:** No permanent free tier. Provides $200 in free initial credits.
*   **Concurrency:** Applied at the project level, lower-tier accounts may be limited to 1 concurrent stream.

---

## Search & Tools Services

### Tavily API (Search)
*   **Free Tier:** 1,000 API credits per month.
*   **Notes:** Unspecified RPM, rate-limited to a "reasonable number" to prevent abuse.

### GetStream.io Chat API
*   **Build Tier (Free):**
    *   **MAU:** Up to 100 Monthly Active Users.
    *   **Concurrent Connections:** 25.
    *   **Rate Limits:** 60 requests per minute per API endpoint.
