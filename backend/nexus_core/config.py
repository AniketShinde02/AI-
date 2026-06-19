import os
from dotenv import load_dotenv

# Load main backend .env specifically
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Provider Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Piper TTS — Offline Fallback (Female Indian Voice)
BASE_PIPER          = "D:/AI/backend/nexus_core/models/piper"
PIPER_FEMALE_MODEL  = os.getenv("PIPER_FEMALE_MODEL", f"{BASE_PIPER}/hi_IN-priyamvada-medium.onnx")



# Groq Whisper (Cheaper STT)
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

# LLM Defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_TEMPERATURE = 0.4

