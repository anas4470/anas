import asyncio
import json
import os
import websockets
import base64
from google import genai

# التأكد من تحميل المفتاح من Render
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
MODEL = "gemini-2.0-flash-exp"

async def gemini_session_handler(client_websocket: websockets.WebSocketServerProtocol, path):
    try:
        config_message = await client_websocket.recv()
        config = json.loads(config_message).get("setup", {})
        config["system_instruction"] = "You are a daily life assistant."
        
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            async def send_to_gemini():
                async for message in client_websocket:
                    data = json.loads(message)
                    if "realtime_input" in data:
                        for chunk in data["realtime_input"]["media_chunks"]:
                            await session.send(input=chunk)

            async def receive_from_gemini():
                async for response in session.receive():
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.text:
                                await client_websocket.send(json.dumps({"text": part.text}))
                            elif part.inline_data:
                                audio_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                                await client_websocket.send(json.dumps({"audio": audio_b64}))
            
            await asyncio.gather(send_to_gemini(), receive_from_gemini())
    except Exception as e:
        print(f"Session Error: {e}")

async def main():
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(gemini_session_handler, "0.0.0.0", port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
