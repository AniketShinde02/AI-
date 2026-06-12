import asyncio
from providers.tts import KokoroTTS
import os

async def test():
    try:
        tts = KokoroTTS(
            model_path="D:/AI/backend/src/backend/voice/models/kokoro-v1.0.fp16-gpu.onnx",
            voices_path="D:/AI/backend/src/backend/voice/models/voices-v1.0.bin"
        )
        print("TTS Init Success")
        
        gen = await tts.stream_audio("Nexus system online. Scanning environment.")
        print("Stream created")
        
        count = 0
        async for chunk in gen:
            count += len(chunk.data)
        
        print(f"Generated {count} bytes of audio")
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(test())
