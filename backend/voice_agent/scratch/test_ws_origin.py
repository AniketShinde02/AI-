import asyncio
import websockets
import json

async def test_ws_with_origin():
    uri = "ws://localhost:8000/ws/nexus"
    # Testing with the origin the browser would send
    headers = {
        "Origin": "http://localhost:3939"
    }
    try:
        print(f"Attempting to connect to {uri} with Origin: {headers['Origin']}...")
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("Connected successfully")
            await websocket.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws_with_origin())
