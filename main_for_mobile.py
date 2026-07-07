import asyncio, os, websockets
from google import genai
from aiohttp import web

# إعداد العميل
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options={'api_version': 'v1alpha'})

async def gemini_handler(request, ws):
    print("WebSocket connection established!")
    async with client.aio.live.connect(model="gemini-2.0-flash-exp") as session:
        async def send():
            async for msg in ws:
                await session.send(input=msg)
        async def receive():
            async for resp in session.receive():
                await ws.send(str(resp))
        await asyncio.gather(send(), receive())

async def health_check(request):
    return web.Response(text="OK")

async def init_app():
    app = web.Application()
    app.router.add_get('/', health_check) # التعامل مع طلبات ريندر العادية
    return app

# تشغيل السيرفر باستخدام websockets و aiohttp معاً
async def main():
    port = int(os.environ.get("PORT", 8080))
    # هذا الكود سيقبل اتصالات الـ WS، وأي طلب آخر سيتم تجاهله أو الرد عليه بـ OK
    async with websockets.serve(gemini_handler, "0.0.0.0", port):
        print(f"Server started on {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
