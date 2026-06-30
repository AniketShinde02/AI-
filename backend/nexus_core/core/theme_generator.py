import httpx
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("nexus.theme_generator")

async def generate_theme_from_image(image_path: str, gemini_api_key: str) -> Dict[str, Any]:
    """
    Sends the uploaded image to Gemini Vision to extract a dark-mode optimized theme palette.
    """
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    import base64
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
    
    prompt = """
    You are an expert UI/UX designer. Analyze the provided image (e.g. an anime character, superhero, landscape).
    Extract a cohesive, modern, dark-mode optimized theme palette for a desktop OS interface based on this image.
    
    Return ONLY a raw JSON object with the following structure (no markdown tags):
    {
        "primary": "#hexcolor",
        "secondary": "#hexcolor",
        "accent": "#hexcolor",
        "background": "#050505", (must be very dark, near black)
        "surface": "#121212", (slightly lighter than background)
        "text": "#ffffff",
        "border": "#hexcolor" (a subtle, low-opacity version of the accent color)
    }
    """
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime_type, "data": encoded_string}}
            ]
        }]
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, timeout=30.0)
        
        if res.status_code != 200:
            logger.error(f"Gemini API Error: {res.text}")
            raise Exception("Failed to generate theme from Gemini.")
            
        data = res.json()
        try:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean markdown formatting if Gemini included it
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            theme_json = json.loads(raw_text)
            return theme_json
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise Exception("Invalid theme format returned from Gemini.")
