import time
import sys
import numpy as np

sys.path.append('d:/AI/backend/voice_agent')
import config
from piper.voice import PiperVoice
from scipy.signal import resample_poly
from math import gcd

try:
    voice = PiperVoice.load(config.PIPER_FEMALE_MODEL, config_path=config.PIPER_FEMALE_MODEL + ".json")
except Exception as e:
    print(f"Failed to load piper: {e}")
    sys.exit(1)

TARGET_SAMPLE_RATE = 16000

def _resample_to_target(samples: np.ndarray, src_rate: int) -> np.ndarray:
    if src_rate == TARGET_SAMPLE_RATE:
        return samples
    audio_f = samples.astype(np.float32) / 32768.0
    g = gcd(TARGET_SAMPLE_RATE, src_rate)
    up = TARGET_SAMPLE_RATE // g
    down = src_rate // g
    resampled_f = resample_poly(audio_f, up, down)
    return np.clip(resampled_f * 32768.0, -32768, 32767).astype(np.int16)

def test_chunk_size(text, chunk_bytes):
    print(f"\nTesting Chunk Size: {chunk_bytes} bytes")
    start = time.time()
    chunks = list(voice.synthesize(text))
    
    all_samples = []
    native_rate = TARGET_SAMPLE_RATE
    for c in chunks:
        if c.audio_int16_array is not None:
            native_rate = c.sample_rate
            all_samples.append(c.audio_int16_array)
            
    if not all_samples:
        return
        
    merged = np.concatenate(all_samples)
    resampled = _resample_to_target(merged, native_rate)
    
    chunk_samples = chunk_bytes // 2 # 16-bit PCM = 2 bytes per sample
    
    first_chunk_time = None
    total_chunks = 0
    
    gen_start = time.time()
    for i in range(0, len(resampled), chunk_samples):
        chunk_out = resampled[i:i + chunk_samples]
        if first_chunk_time is None:
            first_chunk_time = time.time() - start
        total_chunks += 1
        
    end = time.time()
    print(f"Time to First Byte (TTFB): {first_chunk_time:.4f}s")
    print(f"Total time: {end - start:.4f}s")
    print(f"Total chunks emitted: {total_chunks}")
    
text = "This is a benchmark for different chunk sizes in the text to speech audio pipeline."
test_chunk_size(text, 6400)
test_chunk_size(text, 12800)
test_chunk_size(text, 25600)
test_chunk_size(text, 51200)
