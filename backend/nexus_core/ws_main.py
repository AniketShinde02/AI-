import sys
import asyncio

# CRITICAL: Playwright on Windows requires ProactorEventLoop to launch subprocesses.
# SelectorEventLoop (Python 3.12 default on Windows) raises NotImplementedError
# in asyncio.base_events._make_subprocess_transport.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.global_state import lifespan
from api.rest_routes import rest_router, BACKGROUNDS_DIR
from api.websocket_routes import ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus_ws")

app = FastAPI(title="Nexus Voice WebSocket", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/backgrounds", StaticFiles(directory=BACKGROUNDS_DIR), name="backgrounds")

app.include_router(rest_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ws_main:app", host="0.0.0.0", port=8001, ws="wsproto", loop="asyncio", log_level="info", ws_ping_interval=20.0, ws_ping_timeout=20.0, reload=True, reload_excludes=["data/*", "*.db", "*.db-journal", "logs/*", "*.log"])
