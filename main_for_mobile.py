import asyncio
import os
import json
import base64
import websockets
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODEL = "gemini-2.0-flash-exp"

async def gemini_session_handler(websocket):
    print("Mobile Connected!")
    try:
        # انتظار رسالة الـ setup من الموبايل وعدم الانغلاق إذا تأخرت
        try:
            config_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            config = json.loads(config_msg).get("setup", {})
        except:
            config = {"generation_config": {"response_modalities": ["AUDIO"]}}

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API!")
            
            async def send_to_gemini():
                async for message in websocket:
                    data = json.loads(message)
                    if "realtime_input" in data:
                        for chunk in data["realtime_input"].get("media_chunks", []):
                            await session.send(input={"mime_type": chunk["mime_type"], "data": chunk["data"]})
            
            async def receive_from_gemini():
                async for response in session.receive():
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.text:
                                await websocket.send(json.dumps({"text": part.text}))
                            elif part.inline_data:
                                b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send(json.dumps({"audio": b64}))
            
            await asyncio.gather(send_to_gemini(), receive_from_gemini())

    except Exception as e:
        print(f"Session Error: {e}")

async def main():
    # إعدادات ping ضرورية لمنع قطع الاتصال من Render
    async with websockets.serve(gemini_session_handler, "0.0.0.0", int(os.environ.get("PORT", 8080)), ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
