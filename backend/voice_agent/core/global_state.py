import os
import asyncio
import logging
import json
import base64
import time
import wave
import io
import re
from enum import Enum
from typing import Optional, Deque
from contextlib import asynccontextmanager
from collections import deque
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psutil
import platform
import random
from speech_cleaner import cleaner as speech_cleaner
from pydantic import BaseModel
from fastapi import HTTPException
from core.database import db

try:
    import pyautogui
    import pygetwindow as gw
    from PIL import ImageGrab
except ImportError:
    logging.warning("pyautogui or pygetwindow not installed. OS automation tools will be disabled.")
    pyautogui = None
    gw = None
    ImageGrab = None


# Re-use existing provider logic
from providers.stt import GroqSTT
from providers.llm import GroqLLM
from providers.tts import TTSProviderRouter, ProviderStatus
import torch # type: ignore
from silero_vad import load_silero_vad, VADIterator # type: ignore

# Import Backend Tools for Gemini Live Bridge
from tools.system import execute_pc_action
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences, get_user_memory, delete_user_preference

from tools.file_tools import read_file, write_file, read_directory
from tools.third_party_tools import get_weather
from core.rag_oracle import RAGOracle
import core.rag_oracle as rag_oracle_module

# Setup logging
import subprocess
import signal
from collections import deque
from core.gemini_live_manager import GeminiLiveSessionManager

logger = logging.getLogger("nexus_ws")

from dotenv import find_dotenv
# Automatically find .env in parent directories
load_dotenv(find_dotenv(usecwd=True))

# Import config
import config

# Initialize Providers as None, will be set in lifespan startup
stt_provider: Optional[GroqSTT] = None
llm_provider: Optional[GroqLLM] = None
tts_router: Optional[TTSProviderRouter] = None
vad_model = None

import pickle

# Global state for greeting cache
cached_greeting_pcm: list = []
CACHE_FILE = "greeting_cache.pkl"

if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "rb") as f:
            cached_greeting_pcm = pickle.load(f)
            print("[SUCCESS] Loaded cached greeting from disk.")
    except Exception as e:
        print(f"❌ Failed to load greeting cache: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_provider, llm_provider, tts_router, vad_model
    import time
    
    start_time = time.time()
    def log_stage(msg):
        elapsed = time.time() - start_time
        print(f"[{elapsed:.2f}s] {msg}")

    print("\n" + "="*50)
    log_stage("[START] Starting Nexus Voice Providers...")
    try:
        log_stage("1. Initializing Groq STT...")
        stt_provider = GroqSTT(api_key=str(config.GROQ_API_KEY))
        
        log_stage("2. Initializing Groq LLM...")
        llm_provider = GroqLLM(api_key=str(config.GROQ_API_KEY))
        
        log_stage("3. Initializing TTS Router...")
        tts_router = TTSProviderRouter(config)
        
        log_stage("4. Loading Silero VAD...")
        vad_model = load_silero_vad()
        
        log_stage("5. Initializing RAG Oracle...")
        rag_oracle_module.oracle_instance = RAGOracle(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            groq_api_key=str(config.GROQ_API_KEY)
        )
        
        log_stage("6. Initializing Lance Memory...")
        import core.lance_memory as lance_memory_module
        # Initialize globally so first query isn't slow
        lance_memory_module.semantic_memory = lance_memory_module.SemanticMemory(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "")
        )
        
        log_stage("7. Registering capabilities...")
        from core.capabilities import registry
        _caps = [
            ("pc_open_app", "Open Application", "Open a Windows application by name", "applications", False, False),
            ("pc_close_app", "Close Application", "Close a running Windows application", "applications", False, False),
            ("pc_take_screenshot", "Take Screenshot", "Capture the primary display", "screenshots", False, False),
            ("pc_type_text", "Type Text", "Simulate keyboard typing", "keyboard", False, False),
            ("pc_press_shortcut", "Press Shortcut", "Simulate a keyboard shortcut", "keyboard", False, False),
            ("run_scrapper_task", "Run ScrapperOS Task", "Trigger an external web scraper", "automation", True, True),
            ("list_available_scrapers", "List Scrapers", "Fetch available web scrapers", "automation", False, False),
            ("check_scrapper_health", "Scrapper Health", "Check if ScrapperOS is online", "automation", False, False),
        ]
        for cap_id, name, desc, cat, req_perm, req_approval in _caps:
            await registry.register_tool(cap_id, name, desc, cat, req_perm, req_approval, enabled=True)
            
        log_stage("8. Running App Discovery...")
        from core.app_discovery import run_discovery
        asyncio.create_task(run_discovery())
        
        log_stage("[SUCCESS] Providers initialized successfully!")
    except Exception as e:
        log_stage(f"[ERROR] Critical failure during provider initialization: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*50 + "\n")
    yield
    # Shutdown: nothing to explicitly close for these providers

active_sessions = {}
greeting_lock = asyncio.Lock()

