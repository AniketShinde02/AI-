import asyncio
import time
import sys

sys.path.append('d:/AI/backend/nexus_core')
import config
from kokoro_onnx import Kokoro

k = Kokoro(config.KOKORO_MODEL_PATH, config.KOKORO_VOICES_PATH)

async def measure_latency(stop_event):
    latencies = []
    while not stop_event.is_set():
        start = time.time()
        await asyncio.sleep(0.01)
        end = time.time()
        latency = end - start - 0.01
        if latency > 0:
            latencies.append(latency)
    return latencies

async def test_synchronous(text):
    print(f"Testing synchronous generation...")
    stop_event = asyncio.Event()
    
    latency_task = asyncio.create_task(measure_latency(stop_event))
    
    start_time = time.time()
    # Kokoro create_stream is a synchronous generator
    # Iterating over it on the main thread will block the event loop
    stream = k.create_stream(text, voice='hf_alpha')
    for i, (audio, phonemes) in enumerate(stream):
        pass # simulate processing
    
    end_time = time.time()
    stop_event.set()
    latencies = await latency_task
    
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"Max event loop blockage: {max(latencies) if latencies else 0:.4f}s")
    print(f"Average event loop blockage: {sum(latencies)/len(latencies) if latencies else 0:.4f}s")
    return max(latencies) if latencies else 0

async def test_threaded(text):
    print(f"\nTesting threaded generation...")
    stop_event = asyncio.Event()
    
    latency_task = asyncio.create_task(measure_latency(stop_event))
    
    start_time = time.time()
    
    # Threaded version
    def run_stream():
        stream = k.create_stream(text, voice='hf_alpha')
        for i, (audio, phonemes) in enumerate(stream):
            pass # simulate processing
            
    await asyncio.to_thread(run_stream)
    
    end_time = time.time()
    stop_event.set()
    latencies = await latency_task
    
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"Max event loop blockage: {max(latencies) if latencies else 0:.4f}s")
    print(f"Average event loop blockage: {sum(latencies)/len(latencies) if latencies else 0:.4f}s")
    return max(latencies) if latencies else 0

async def main():
    text = "Hello, this is a longer sentence to test the generation delay. We want to see if the asyncio event loop gets blocked during the generation of the audio."
    
    await test_synchronous(text)
    await test_threaded(text)
    
if __name__ == "__main__":
    asyncio.run(main())
