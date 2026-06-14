import os
from dotenv import load_dotenv
from google import genai

load_dotenv("d:\\AI\\backend\\.env")
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models = client.models.list()
for m in models:
    if "flash" in m.name or "audio" in m.name:
        print(f"Model: {m.name}")
