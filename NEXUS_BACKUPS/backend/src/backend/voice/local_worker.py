import os
import io
import time
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from kokoro_onnx import Kokoro
import numpy as np
import soundfile as sf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus-local-worker")

app = FastAPI(title="Nexus Local High-Durability TTS Worker")

# --- TTS Setup (Kokoro-82M) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KOKORO_MODEL_PATH = os.path.join(SCRIPT_DIR, "models", "kokoro-v1.0.fp16-gpu.onnx")
VOICES_PATH = os.path.join(SCRIPT_DIR, "models", "voices-v1.0.bin")

kokoro = None
if os.path.exists(KOKORO_MODEL_PATH):
    logger.info(f"Loading Kokoro TTS Model from {KOKORO_MODEL_PATH}...")
    try:
        # Check if voices path exists, otherwise try loading without it (uses internal)
        if os.path.exists(VOICES_PATH):
            kokoro = Kokoro(KOKORO_MODEL_PATH, VOICES_PATH)
        else:
            logger.warning(f"Voices file not found at {VOICES_PATH}, attempting to load with defaults...")
            kokoro = Kokoro(KOKORO_MODEL_PATH)
    except Exception as e:
        logger.error(f"Failed to load Kokoro: {e}")
else:
    logger.warning(f"Kokoro model files not found at {KOKORO_MODEL_PATH}. TTS will be unavailable.")

@app.post("/tts")
async def generate_speech(text: str = Form(...), voice: str = Form("af_sarah")):
    """Generate speech using Kokoro-82M (CPU Optimized)."""
    if not kokoro:
        return {"error": "TTS model not loaded"}, 500
        
    start_time = time.time()
    
    try:
        # Generate audio samples (float32, 24000Hz)
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        
        # Convert to 16-bit PCM (standard for most streaming SDKs)
        # Ensure we don't overflow
        samples = (samples * 32767).astype(np.int16)
        
        duration = time.time() - start_time
        logger.info(f"TTS Generated (Raw PCM): '{text[:30]}...' in {duration:.2f}s")
        
        return StreamingResponse(io.BytesIO(samples.tobytes()), media_type="audio/l16; rate=24000")
    except Exception as e:
        logger.error(f"TTS Generation Error: {e}")
        return {"error": str(e)}, 500

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "tts_ready": kokoro is not None,
        "engine": "Kokoro-82M ONNX"
    }

@app.get("/voices")
async def list_voices():
    if not kokoro:
        return {"error": "TTS model not loaded"}, 500
    try:
        return {"voices": kokoro.get_voices()}
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # Ensure models directory exists
    os.makedirs("models", exist_ok=True)
    port = int(os.getenv("PORT", 8001))
    logger.info(f"Starting Nexus Local TTS Worker on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
