import sys
import os
from piper.voice import PiperVoice

model_path = "D:/AI/backend/voice_agent/models/piper/en_US-amy-low.onnx"
config_path = "D:/AI/backend/voice_agent/models/piper/en_US-amy-low.onnx.json"

try:
    voice = PiperVoice.load(model_path, config_path=config_path)
    chunks = voice.synthesize("Hello")
    for chunk in chunks:
        print(dir(chunk))
        break
except Exception as e:
    print("Error:", repr(e))
