import asyncio, json, os, websockets
from google import genai

# 1. تعريف العميل بشكل صريح
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})

async def handle_connection(websocket):
    print("Connection incoming...")
    try:
        # اتصال مباشر بدون تعقيدات
        async with client.aio.live.connect(model="gemini-2.0-flash-exp") as session:
            print("Session established!")
            
            async def from_mobile():
                async for message in websocket:
                    await session.send(input=json.loads(message))
            
            async def to_mobile():
                async for response in session.receive():
                    await websocket.send(json.dumps({"data": str(response)}))
            
            await asyncio.gather(from_mobile(), to_mobile())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # هذا السطر سيطبع الخطأ الحقيقي في Logs ريندر (هو اللي هيقولنا ليه الـ pipe اتكسر)

async def main():
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(handle_connection, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
