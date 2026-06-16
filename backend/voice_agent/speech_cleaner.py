import os
from groq import AsyncGroq
import logging
import time

logger = logging.getLogger("nexus.speech_cleaner")

class SpeechCleaner:
    def __init__(self):
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
        Passes raw STT text through a fast LLM to remove filler words,
        fix punctuation, and normalize sentence structure.
        """
        self._init_client()
        if not self.client or not raw_text.strip():
            return raw_text

        # Heuristic 1: Very short standard phrases
        lower_text = raw_text.lower().strip(".?!, ")
        if lower_text in ["yes", "no", "hello", "hi", "hey", "stop", "okay", "ok"]:
            return raw_text

        # Heuristic 2: Known filler prefixes
        cleaned = raw_text
        for filler in ["umm ", "uhh ", "like ", "actually ", "so ", "yaar ", "bro ", "listen "]:
            if cleaned.lower().startswith(filler):
                cleaned = cleaned[len(filler):].strip()
        
        # If the string is now very short, skip LLM to save latency
        if len(cleaned.split()) <= 3:
            return cleaned.capitalize()

        start_time = time.perf_counter()
        
        system_prompt = (
            "You are a real-time speech normalizer. "
            "Your ONLY job is to remove stutters, remove repeated words, and fix spacing. "
            "CRITICAL RULES:\n"
            "1. DO NOT translate. If the input is Hindi or Hinglish, keep it exactly in that language.\n"
            "2. DO NOT paraphrase, summarize, or rewrite the intent.\n"
            "3. DO NOT infer meaning. Preserve semantics 100%.\n"
            "4. Output ONLY the normalized text. Do NOT answer the user."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Clean this: {raw_text}"}
                ],
                temperature=0.0,
                max_tokens=256
            )
            
            clean_text = response.choices[0].message.content.strip()
            
            # Prevent the LLM from over-apologizing or failing gracefully in the output string
            if clean_text.lower().startswith("here is the clean") or clean_text.lower().startswith("clean text:"):
                clean_text = clean_text.split(":", 1)[-1].strip()
                
            latency = time.perf_counter() - start_time
            logger.info(f"🧹 [SpeechCleaner] {latency*1000:.0f}ms | Raw: '{raw_text}' -> Clean: '{clean_text}'")
            return clean_text

        except Exception as e:
            logger.error(f"❌ [SpeechCleaner] Failed: {e}")
            return raw_text

# Singleton instance
cleaner = SpeechCleaner()
