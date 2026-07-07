import websockets
import asyncio

async def handler(websocket):
    # كود الربط مع جمناي الخاص بك هنا
    async for message in websocket:
        # معالجة الرسائل
        pass

# التعديل الأهم: إضافة فحص للطلبات قبل بدء الـ Handshake
async def custom_handshake(websocket, path):
    # هذه الدالة ستسمح فقط بطلبات GET
    if websocket.request.method != "GET":
        return False
    return None

# عند تشغيل السيرفر
async def main():
    async with websockets.serve(
        handler, "0.0.0.0", 8080, 
        process_request=custom_handshake # هنا نمرر الفحص
    ):
        await asyncio.Future()  # تشغيل السيرفر للأبد

asyncio.run(main())
