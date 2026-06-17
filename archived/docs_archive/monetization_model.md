# Monetization Model: Tiers, Quotas & Limits

## 1. Value Proposition
Nexus 2.0 provides high-performance voice AI with deep OS/Browser integration. To sustain this, we use a tiered quota system to manage LLM and Voice costs.

## 2. Subscription Tiers

### Tier 0: Free (Beta/Testing)
- **Voice Minutes**: 30 minutes/month.
- **LLM**: GPT-4o-mini / Llama 3.1 70B (Groq).
- **Deep Research**: 2 tasks/month.
- **Tools**: Browser only (Basic).
- **Retention**: 7-day memory.

### Tier 1: Pro ($19/month)
- **Voice Minutes**: 300 minutes/month.
- **LLM**: GPT-4o / Claude 3.5 Sonnet.
- **Deep Research**: Unlimited.
- **Tools**: Full Browser + Windows Agent (Desktop).
- **Retention**: Permanent memory + Document indexing.
- **Speed**: Priority queue for Groq/Stream.

### Tier 2: Developer (Self-Hosted/API Keys)
- **Voice Minutes**: Bring your own (Deepgram/ElevenLabs keys).
- **LLM**: Bring your own (OpenAI/Anthropic keys).
- **Deep Research**: Unlimited.
- **Tools**: Full Access.
- **Feature**: Access to raw agent logs and LangGraph visualizer.

## 3. Quota Management Logic
Quotas are tracked in the `user_usage` table in Supabase.

1.  **Voice**: Tracked via Stream `call_duration` events.
2.  **LLM Tokens**: Aggregated per request.
3.  **Research**: Incremented on `research_task` completion.

## 4. Abuse Prevention
- **Concurrent Sessions**: Max 1 active voice session per user.
- **Rate Limiting**: 5 requests/second on the API layer.
- **Budgeting**: Hard cap on `$0.50` cost per single "Research" task to prevent runaway agent loops.
