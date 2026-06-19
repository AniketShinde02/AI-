import asyncio
import time
import sys

sys.path.append('d:/AI/backend/nexus_core')
import config
from piper.voice import PiperVoice

try:
    voice = PiperVoice.load(config.PIPER_FEMALE_MODEL, config_path=config.PIPER_FEMALE_MODEL + ".json")
except Exception as e:
    print(f"Failed to load piper: {e}")
    sys.exit(1)

async def measure_latency(stop_event):
    latencies = []
    while not stop_event.is_set():
        start = time.time()
        await asyncio.sleep(0.01)
        end = time.time()
        latency = end - start - 0.01
        if latency > 0.005:  # filter tiny jitter
            latencies.append(latency)
    return latencies

async def test_synchronous(text):
    print(f"Testing synchronous Piper generation...")
    stop_event = asyncio.Event()
    latency_task = asyncio.create_task(measure_latency(stop_event))
    
    start_time = time.time()
    
    # Run blocking piper synthesis directly on event loop
    chunks = list(voice.synthesize(text))
    
    end_time = time.time()
    stop_event.set()
    latencies = await latency_task
    
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"Max event loop blockage: {max(latencies) if latencies else 0:.4f}s")
    return max(latencies) if latencies else 0

async def test_threaded(text):
    print(f"\nTesting threaded Piper generation...")
    stop_event = asyncio.Event()
    latency_task = asyncio.create_task(measure_latency(stop_event))
    
    start_time = time.time()
    
    # Run blocking piper synthesis in thread pool
    chunks = await asyncio.to_thread(lambda: list(voice.synthesize(text)))
    
    end_time = time.time()
    stop_event.set()
    latencies = await latency_task
    
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"Max event loop blockage: {max(latencies) if latencies else 0:.4f}s")
    return max(latencies) if latencies else 0

async def main():
    text = "Hello, this is a longer sentence to test the generation delay. We want to see if the asyncio event loop gets blocked during the generation of the audio."
    
    await test_synchronous(text)
    await test_threaded(text)
    
if __name__ == "__main__":
    asyncio.run(main())
