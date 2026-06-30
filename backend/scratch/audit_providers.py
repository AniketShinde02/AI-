import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("d:/AI/backend/.env")

providers = [
    ("Groq", "https://api.groq.com/openai/v1/models", os.environ.get("GROQ_API_KEY")),
    ("Cerebras", "https://api.cerebras.ai/v1/models", os.environ.get("CEREBRAS_API_KEY")),
    ("Mistral", "https://api.mistral.ai/v1/models", os.environ.get("MISTRAL_API_KEY")),
    ("OpenRouter", "https://openrouter.ai/api/v1/models", os.environ.get("OPENROUTER_API_KEY"))
]

async def check_models():
    results = {}
    async with httpx.AsyncClient() as client:
        for name, url, key in providers:
            if not key:
                print(f"Skipping {name}: no API key")
                continue
            
            try:
                resp = await client.get(url, headers={"Authorization": f"Bearer {key}"})
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    results[name] = models
                    print(f"=== {name} Models ===")
                    for m in models: print(f"- {m}")
                else:
                    print(f"Failed {name}: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Error {name}: {e}")
    
    with open("d:/AI/backend/scratch/model_audit.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(check_models())
