import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv("d:\\AI\\backend\\.env")
api_key = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {bool(api_key)}")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="Hello, this is a test.",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            )
        )
    )
    print("Success with gemini-2.5-flash!")
except Exception as e:
    print("Failed with gemini-2.5-flash:", str(e))

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents="Hello, this is a test.",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            )
        )
    )
    print("Success with gemini-2.0-flash-exp!")
except Exception as e:
    print("Failed with gemini-2.0-flash-exp:", str(e))
