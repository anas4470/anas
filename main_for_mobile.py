import asyncio
import os
import json
import websockets
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

async def handler(websocket):
    print("Mobile Connected!")
    async with client.aio.live.connect(model="gemini-2.0-flash-exp") as session:
        async def listen_to_mobile():
            async for message in websocket:
                data = json.loads(message)
                if "realtime_input" in data:
                    await session.send(input=data["realtime_input"])
        
        async def send_to_mobile():
            async for response in session.receive():
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text:
                            await websocket.send(json.dumps({"text": part.text}))
        
        await asyncio.gather(listen_to_mobile(), send_to_mobile())

async def main():
    async with websockets.serve(handler, "0.0.0.0", int(os.environ.get("PORT", 8080))):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
