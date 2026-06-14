from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

app = FastAPI()

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive()
    print("Received data:", data)
    print("'bytes' in data:", "bytes" in data)
    print("'text' in data:", "text" in data)

client = TestClient(app)
with client.websocket_connect("/ws") as websocket:
    websocket.send_text("hello")
