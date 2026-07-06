import asyncio
import os
import json
import base64
import websockets
from google import genai

# التحقق من الـ API Key في الـ Logs عند بدء التشغيل
api_key = os.environ.get("GEMINI_API_KEY")
print(f"DEBUG: API Key Status: {'FOUND' if api_key else 'MISSING'}")
if api_key:
    print(f"DEBUG: Key starts with: {api_key[:4]}****")

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODEL = "gemini-2.0-flash-exp"

async def gemini_session_handler(websocket):
    print("Mobile Connected!")
    
    # إعدادات ثابتة لتجنب تعقيدات الـ setup من الموبايل في البداية
    config = {
        "generation_config": {"response_modalities": ["AUDIO"]},
        "system_instruction": "أنت رفيق، مساعد صوتي لمستخدم كفيف. صف الصور بدقة."
    }

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API successfully!")
            
            # مهام الاستقبال والإرسال
            async def send_to_gemini():
                async for message in websocket:
                    data = json.loads(message)
                    if "realtime_input" in data:
                        media_chunks = data["realtime_input"].get("media_chunks", [])
                        for chunk in media_chunks:
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
        print(f"CRITICAL ERROR in Gemini Session: {e}")

async def main():
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(gemini_session_handler, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
