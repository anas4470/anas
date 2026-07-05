import asyncio
import json
import os
import websockets
import base64
from google import genai

# إعداد مفتاح الـ API من متغيرات البيئة في Render
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
MODEL = "gemini-2.0-flash-exp"

async def gemini_session_handler(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            if "setup" in data:
                # إعداد الاتصال بجيمناي
                async with client.aio.live.connect(model=MODEL) as session:
                    print("Connected to Gemini")
                    # معالجة الرسائل القادمة والمغادرة
                    async def receive_from_gemini():
                        async for response in session.receive():
                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.text:
                                        await websocket.send(json.dumps({"text": part.text}))
                    
                    await receive_from_gemini()
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # هذا هو السطر الأهم: يقرأ البورت الذي يحدده Render
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(gemini_session_handler, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
