# Gemini API Rate Limits & Implementation Strategy

## Overview
To prevent `429 Too Many Requests` or `Quota Exceeded` errors, the system must respect the rate limits of the Google Gemini API. Since Nexus uses the Gemini API heavily for Text-To-Speech (TTS), limits can be exhausted quickly if multiple sentences are streamed sequentially without pacing.

## Rate Limits Table (Free Tier)

| Model Name | Requests Per Minute (RPM) | Tokens Per Minute (TPM) | Requests Per Day (RPD) |
| :--- | :--- | :--- | :--- |
| **Gemini 2.5 Flash / 1.5 Flash** | 15 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 1.5 Pro** | 2 RPM | 32,000 TPM | 50 RPD |
| **Gemini 1.0 Pro** | 15 RPM | 32,000 TPM | 1,500 RPD |
| **Text Embedding** | 1,500 RPM | N/A | 1,500 RPD |

*Note: Paid tiers have significantly higher limits.*

## Nexus Implementation Details

1. **The Problem:** 
   Because Nexus performs "semantic chunking" (processing the LLM output sentence-by-sentence to reduce time-to-first-audio), a single paragraph might result in 4 to 5 separate TTS requests. With an RPM of 15, the API will hit a `429 Too Many Requests` error after just 3-4 conversational turns in a minute.
   
2. **The Solution (Retry with Exponential Backoff):**
   In `tts_gemini.py`, a robust backoff mechanism has been implemented. When a `429` error is encountered:
   - The system catches the error.
   - It triggers an exponential backoff formula: `(2 ^ retry_count) + random_jitter`.
   - The thread sleeps to wait out the rate-limit window.
   - It then safely retries the request without crashing the backend or losing the TTS chunk.
   
3. **Future Considerations:**
   If rate limits become a recurring blocker during intense testing, consider either batching larger chunks of text (e.g., waiting for paragraphs rather than sentences) or migrating the API key to a Pay-As-You-Go Google Cloud billing account, which immediately lifts the RPM from 15 to 1000+.
