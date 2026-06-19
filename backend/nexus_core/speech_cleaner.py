import os
from groq import AsyncGroq
import logging
import time

logger = logging.getLogger("nexus.speech_cleaner")

class SpeechCleaner:
    def __init__(self):
        # Llama 3.1 8B is perfect for this—fast and understands Hinglish incredibly well
        self.model = "llama-3.1-8b-instant"
        self.client = None
        self._initialized = False

    def _init_client(self):
        if self._initialized:
            return
        self._initialized = True
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("No GROQ_API_KEY found, SpeechCleaner will passthrough.")
            self.client = None
        else:
            self.client = AsyncGroq(api_key=api_key)

    async def clean(self, raw_text: str) -> str:
        """
        Refines raw STT text into readable sentences with perfect punctuation,
        preserving the raw emotional vibe, fillers, and Hinglish vocabulary.
        """
        self._init_client()
        if not self.client or not raw_text.strip():
            return raw_text

        # Heuristic: Quick pass-through for ultra-short standard single words
        lower_text = raw_text.lower().strip(".?!, ")
        if lower_text in ["yes", "no", "hello", "hi", "hey", "stop", "okay", "ok"]:
            return raw_text.capitalize()

        start_time = time.perf_counter()
        
        # Rewritten System Prompt to maintain the "Jaan" and raw emotion
        system_prompt = (
            "You are the real-time speech processing frontend for NEXUS, an advanced personal AI.\n"
            "Your job is to fix broken audio-to-text transcripts into clean, punctuated prose while keeping 100% of the personality.\n\n"
            "CRITICAL RULES:\n"
            "1. DO NOT sanitize or elegantize. If the user uses slang, Hinglish, or informal street words ('yaar', 'bro', 'launda', 'bhai', 'scen', 'vibe'), PRESERVE them exactly.\n"
            "2. Add aggressive, accurate punctuation (commas, question marks, exclamation marks) to reflect the emotional cadence and pauses of the spoken voice.\n"
            "3. Only remove literal audio stutters (e.g., 'me me meine' -> 'meine', 'i i want' -> 'I want'). Do not drop words that add rhythm or emotional context.\n"
            "4. Never reply to the content. Output ONLY the polished user text."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Clean transcript: {raw_text}"}
                ],
                temperature=0.1,  # Low temperature keeps it precise, slightly above 0.0 allows better context mapping
                max_tokens=256
            )
            
            clean_text = response.choices[0].message.content.strip()
            
            # Clean up potential LLM conversational leaks
            if clean_text.lower().startswith("clean transcript:"):
                clean_text = clean_text.split(":", 1)[-1].strip()
            
            # Direct quote removal if model wraps it
            if clean_text.startswith('"') and clean_text.endswith('"'):
                clean_text = clean_text[1:-1].strip()
                
            latency = time.perf_counter() - start_time
            logger.info(f"🧹 [SpeechCleaner] {latency*1000:.0f}ms | Raw: '{raw_text}' -> Clean: '{clean_text}'")
            return clean_text

        except Exception as e:
            logger.error(f"❌ [SpeechCleaner] Failed: {e}")
            return raw_text

# Singleton instance
cleaner = SpeechCleaner()
