import os
from dotenv import load_dotenv
from getstream import Stream

# Load main backend .env specifically
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Stream API
STREAM_API_KEY = os.getenv("STREAM_API_KEY")
STREAM_API_SECRET = os.getenv("STREAM_API_SECRET")

# Automatically generate STREAM_TOKEN
if STREAM_API_KEY and STREAM_API_SECRET:
    client = Stream(api_key=STREAM_API_KEY, api_secret=STREAM_API_SECRET)
    STREAM_TOKEN = client.create_token("nexus-agent")
else:
    STREAM_TOKEN = os.getenv("STREAM_TOKEN")

# Scale config
MAX_CONCURRENT_CALLS = int(os.getenv("MAX_CONCURRENT_CALLS", "50"))
AGENT_IDLE_TIMEOUT = 120.0 # Seconds before agent leaves an empty room

# Provider Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



# Piper TTS — Offline Fallback (Female Indian Voice)
BASE_PIPER          = "D:/AI/backend/voice_agent/models/piper"
PIPER_FEMALE_MODEL  = os.getenv("PIPER_FEMALE_MODEL", f"{BASE_PIPER}/hi_IN-priyamvada-medium.onnx")



# Groq Whisper (Cheaper STT)
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

# LLM Defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_TEMPERATURE = 0.4

