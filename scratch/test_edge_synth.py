import edge_tts
import asyncio

async def test():
    text = "Hello, this is a test of Microsoft Edge Text-to-Speech."
    communicate = edge_tts.Communicate(text, "en-US-EmmaMultilingualNeural")
    await communicate.save("d:/AI/scratch/test.mp3")
    print("Saved test.mp3")

if __name__ == "__main__":
    asyncio.run(test())
