import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import numpy as np

load_dotenv("d:\\AI\\backend\\.env")
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model='gemini-2.5-flash-preview-tts',
    contents=f"Generate audio from the following text transcript without any extra commentary:\n\nHello, this is a test.",
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

audio_bytes = response.candidates[0].content.parts[0].inline_data.data
chunk_array = np.frombuffer(audio_bytes, dtype=np.int16)
max_amplitude = np.max(np.abs(chunk_array))
print(f"Max amplitude: {max_amplitude} (Max possible is 32767)")
if max_amplitude < 100:
    print("WARNING: Audio is essentially silence!")
else:
    print("Audio contains loud signals!")
