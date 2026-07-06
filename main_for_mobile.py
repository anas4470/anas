import asyncio
import json
import os
import websockets
from google import genai
import base64

# ضبط مفتاح الـ API
os.environ['GOOGLE_API_KEY'] = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash-exp"

client = genai.Client(http_options={'api_version': 'v1alpha'})

async def gemini_session_handler(websocket, path):
    """معالجة جلسة الـ WebSocket مع حماية من الأخطاء."""
    print("New connection attempt...")
    try:
        # انتظر رسالة الـ setup الأولى فقط
        config_message = await websocket.recv()
        config_data = json.loads(config_message)
        config = config_data.get("setup", {})
        config["system_instruction"] = "You are a helpful and friendly daily life assistant."

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API successfully")
           
            async def send_to_gemini():
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        if "realtime_input" in data:
                            await session.send(input=data["realtime_input"])
                except Exception as e:
                    print(f"Error in send: {e}")

            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.text:
                                    await websocket.send(json.dumps({"text": part.text}))
                                elif part.inline_data:
                                    base64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    await websocket.send(json.dumps({"audio": base64_audio}))
                except Exception as e:
                    print(f"Error in receive: {e}")

            await asyncio.gather(send_to_gemini(), receive_from_gemini())

    except Exception as e:
        print(f"Session error: {e}")
    finally:
        print("Session closed.")

async def main():
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(gemini_session_handler, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future()  # تشغيل السيرفر للأبد

if __name__ == "__main__":
    asyncio.run(main())
