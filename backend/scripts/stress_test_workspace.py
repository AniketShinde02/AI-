import asyncio
import time
import sys
import psutil
from core.workspace.workspace_manager import workspace_manager

async def run_stress_test(iterations=1000):
    print(f"Starting Stress Test: {iterations} iterations of workspace_manager.get()...")
    
    start_time = time.monotonic()
    success_count = 0
    error_count = 0
    
    # Track CPU and memory before
    process = psutil.Process()
    cpu_before = process.cpu_percent()
    mem_before = process.memory_info().rss / 1024 / 1024 # MB
    
    latencies = []
    
    for i in range(iterations):
        iter_start = time.monotonic()
        try:
            state = await workspace_manager.get("stress_session")
            success_count += 1
            if not state:
                raise ValueError("State is empty")
        except Exception as e:
            error_count += 1
            print(f"Error at iteration {i}: {e}")
        
        latencies.append((time.monotonic() - iter_start) * 1000) # ms
        
        # Give event loop a tiny breather to simulate real-world websocket event loop
        if i % 100 == 0:
            await asyncio.sleep(0.01)
            
    end_time = time.monotonic()
    
    cpu_after = process.cpu_percent()
    mem_after = process.memory_info().rss / 1024 / 1024 # MB
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    
    print("\n--- Stress Test Results ---")
    print(f"Total Requests  : {iterations}")
    print(f"Success         : {success_count}")
    print(f"Errors          : {error_count}")
    print(f"Total Time      : {end_time - start_time:.2f} s")
    print(f"Avg Latency     : {avg_latency:.2f} ms")
    print(f"Max Latency     : {max_latency:.2f} ms")
    print(f"Min Latency     : {min_latency:.2f} ms")
    print(f"Memory Diff     : {mem_after - mem_before:.2f} MB")
    
    if error_count == 0 and avg_latency < 50:
        print("\nPASS: Stress test completed successfully within acceptable latency limits.")
        sys.exit(0)
    else:
        print("\nFAIL: Errors occurred or latency too high.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_stress_test(1000))
