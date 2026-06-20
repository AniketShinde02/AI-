import os
from dotenv import load_dotenv

# Load main backend .env specifically
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# =============================================================================
# Provider API Keys — Shadow Army Tier System
# =============================================================================

# Knights / Fast Routing (Groq — Sub-200ms JSON compliance)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Grand Marshal / Generals (Cerebras — 1000 RPM, extreme throughput)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Grand Marshal / Planning (Mistral — High reasoning, precise tool calls)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Grand Marshal / Shadow Soldiers (SambaNova — 405B planning + 3B cheap tasks)
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")

# Eyes (Gemini — Vision, streaming audio, multimodal)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenRouter (Fallback pool — free tier models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# =============================================================================
# Speech & Audio
# =============================================================================

# Groq Whisper (STT)
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

# Piper TTS — Offline Fallback (Female Indian Voice)
BASE_PIPER         = "D:/AI/backend/nexus_core/models/piper"
PIPER_FEMALE_MODEL = os.getenv("PIPER_FEMALE_MODEL", f"{BASE_PIPER}/hi_IN-priyamvada-medium.onnx")

# ElevenLabs / Cartesia TTS
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
CARTESIA_API_KEY   = os.getenv("CARTESIA_API_KEY")

# =============================================================================
# LLM Defaults (used as hardcoded fallbacks only)
# =============================================================================
DEFAULT_MODEL       = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_TEMPERATURE = 0.4
