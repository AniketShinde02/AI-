import logging
from groq import AsyncGroq

logger = logging.getLogger("nexus.stt")

class GroqSTT:
    def __init__(self, api_key: str):
        # We just need the client. ws_main.py handles its own audio chunking and transcription loop.
        self.client = AsyncGroq(api_key=api_key)
