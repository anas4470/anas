import asyncio
import json
import os
import websockets
from google import genai

# التأكد من وجود مفتاح الـ API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing!")

client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
MODEL = "gemini-2.0-flash-exp"

async def gemini_session_handler(websocket):
    print("Client connected!")
    try:
        async with client.aio.live.connect(model=MODEL) as session:
            async def send_to_gemini():
                async for message in websocket:
                    data = json.loads(message)
                    if "realtime_input" in data:
                        for chunk in data["realtime_input"]["media_chunks"]:
                            await session.send(input={"mime_type": chunk["mime_type"], "data": chunk["data"]})
            
            async def receive_from_gemini():
                async for response in session.receive():
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.text:
                                await websocket.send(json.dumps({"text": part.text}))
                            elif part.inline_data:
                                import base64
                                b64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                await websocket.send(json.dumps({"audio": b64_audio}))
            
            await asyncio.gather(send_to_gemini(), receive_from_gemini())
    except Exception as e:
        print(f"Session error: {e}")

async def main():
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(gemini_session_handler, "0.0.0.0", port):
        print(f"Server running on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
