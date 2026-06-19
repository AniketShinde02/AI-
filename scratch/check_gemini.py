import os
from google import genai
from dotenv import load_dotenv

# Load env from backend/nexus_core/.env
load_dotenv("d:/AI/backend/nexus_core/.env")

api_key = os.getenv("GEMINI_API_KEY")
print("API Key:", api_key[:10] + "..." + api_key[-5:] if api_key else "None")

client = genai.Client(api_key=api_key)
try:
    # Let's list models or get details
    for model in client.models.list():
        if 'tts' in model.name:
            print("Found model:", model.name)
except Exception as e:
    print("Error:", e)

