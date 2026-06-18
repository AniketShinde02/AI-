# Gemini API Rate Limits & Implementation Strategy

## Overview
To prevent `429 Too Many Requests` or `Quota Exceeded` errors, the system must respect the rate limits of the Google Gemini API. Since Nexus uses the Gemini API heavily for Text-To-Speech (TTS), limits can be exhausted quickly if multiple sentences are streamed sequentially without pacing.

## Rate Limits Table (Free Tier & Live Status)

| Model Name | Category | Requests Per Minute (RPM) | Tokens Per Minute (TPM) | Requests Per Day (RPD) |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.5 Flash-001** | Multimodal (large text/audio) | 25.0 RPM | 4,000,000 TPM | 1,000 RPD |
| **Gemini 3.5 Pro-001** | Text & multimodal | 5.0 RPM | 100,000 TPM | 50.0 RPD |
| **Dall-E** | Images | 5.0 RPM | N/A | 5.0 RPD |
| **Imagen 3 Generate** | Images | 5.0 RPM | N/A | 5.0 RPD |
| **Imagen 3 Edit** | Images | 5.0 RPM | N/A | 5.0 RPD |
| **Imagen 3 Edit (Inpainting/Outpainting)** | Images | 5.0 RPM | N/A | 5.0 RPD |
| **Gemini 2.5 Pro** | Text & multimodal | 2.0 RPM | 32,000 TPM | 50.0 RPD |
| **Gemini 2.5 Flash** | Multimodal (large text/audio) | 15.0 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 2.5 Flash-Lite** | Multimodal (large text/audio) | 30.0 RPM | 2,000,000 TPM | 2,000 RPD |
| **Gemini 2.0 Pro** | Text & multimodal | 2.0 RPM | 32,000 TPM | 50.0 RPD |
| **Gemini 2.0 Flash** | Multimodal (large text/audio) | 15.0 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 2.0 Flash-Lite** | Multimodal (large text/audio) | 30.0 RPM | 2,000,000 TPM | 2,000 RPD |
| **Gemini 2.0 Flash-Thinking** | Text & multimodal | 10.0 RPM | 7,500,000 TPM | 1,500 RPD |
| **Gemini 1.5 Pro-002** | Text & multimodal | 2.0 RPM | 32,000 TPM | 50.0 RPD |
| **Gemini 1.5 Flash-002** | Multimodal (large text/audio) | 15.0 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 1.5 Pro-001** | Text & multimodal | 2.0 RPM | 32,000 TPM | 50.0 RPD |
| **Gemini 1.5 Flash-001** | Multimodal (large text/audio) | 15.0 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 1.5 Pro** | Text & multimodal | 2.0 RPM | 32,000 TPM | 50.0 RPD |
| **Gemini 1.5 Flash** | Multimodal (large text/audio) | 15.0 RPM | 1,000,000 TPM | 1,500 RPD |
| **Gemini 1.0 Pro-001** | Text & multimodal | 15.0 RPM | 32,000 TPM | 1,500 RPD |
| **Gemini 1.0 Pro** | Text & multimodal | 15.0 RPM | 32,000 TPM | 1,500 RPD |
| **Gemini Embedding 004** | Embeddings | 1,500.0 RPM | 9,000,000 TPM | 3,000 RPD |
| **Gemini Embedding 004 (Batch)** | Embeddings | 3.0 RPM | 9,000,000 TPM | 3,000 RPD |
| **Gemini Semantic Retriever (API Key)** | Semantic Search | 10.0 RPM | 9,000,000 TPM | 3,000 RPD |
| **Gemini Semantic Retriever (OAuth)** | Semantic Search | 30.0 RPM | 9,000,000 TPM | 3,000 RPD |
| **Gemini 1.5 DE** | Text & multimodal | 20.0 RPM | 1,000,000 TPM | 2,000 RPD |
| **Gemini 1.5 SE** | Text & multimodal | 20.0 RPM | 1,000,000 TPM | 2,000 RPD |
| **Imagen 4 AI Generate** | Text-to-image/video generation | N/A | N/A | 3,000 RPD |
| **Imagen 4 Generate** | Text-to-image/video generation | N/A | N/A | 3,000 RPD |
| **Imagen 4 Ultra Generate** | Text-to-image/video generation | N/A | N/A | 50.0 RPD |
| **AQA Model** | Text-and-code models | 10.0 RPM | 5.0 TPM | 20.0 RPD |
| **AQA Model 2** | Text-and-code models | 10.0 RPM | 5.0 TPM | 20.0 RPD |
| **The Off-API-Models v2** | Text-and-code models | 10.0 RPM | 5.0 TPM | 20.0 RPD |
| **The Off-API-Models v3** | Text-and-code models | 10.0 RPM | 5.0 TPM | 20.0 RPD |
| **Data Extraction v1** | Text-and-code models | 20.0 RPM | N/A | 20.0 RPD |
| **Gemini 2.5 Flash-Lite (Voice)** | Voice | 30.0 RPM | 2,000,000 TPM | 2,000 RPD |
| **Gemini 1.5 Flash-Lite (Voice)** | Voice | 30.0 RPM | 2,000,000 TPM | 2,000 RPD |
| **Gemini 2.0 Live Prototype** | Voice | 30.0 RPM | 2,000,000 TPM | 2,000 RPD |

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
