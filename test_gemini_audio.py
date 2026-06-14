import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import wave
import io

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
print(f"Total bytes received: {len(audio_bytes)}")

try:
    with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_file:
        print(f"Channels: {wav_file.getnchannels()}")
        print(f"Sample width: {wav_file.getsampwidth()}")
        print(f"Frame rate: {wav_file.getframerate()}")
        print(f"Num frames: {wav_file.getnframes()}")
except Exception as e:
    print("Not a WAV file!", e)
