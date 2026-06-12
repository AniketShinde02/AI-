import sys
import os
from piper.voice import PiperVoice

try:
    help(PiperVoice.synthesize)
except Exception as e:
    print("Error:", repr(e))
