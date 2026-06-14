import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv("d:\\AI\\backend\\.env")
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-tts',
        contents=f"Generate audio from the following text transcript without any extra commentary:\n\n{ 'Hello, this is a test.' }",
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
    print("Success with gemini-2.5-flash-preview-tts!")
    audio_bytes = response.candidates[0].content.parts[0].inline_data.data
    print(f"Got {len(audio_bytes)} bytes of audio!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("Failed with gemini-2.5-flash-preview-tts:", str(e))
