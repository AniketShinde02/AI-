import os
import asyncio
from groq import AsyncGroq
import io
import wave

async def test():
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # write 1 second of silence
        wf.writeframes(b'\x00' * 32000)
    
    buffer.seek(0)
    buffer.name = "audio.wav"
    try:
        res = await client.audio.transcriptions.create(
            file=buffer,
            model="whisper-large-v3",
            response_format="text",
            language="en"
        )
        print("Success:", repr(res))
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(test())
