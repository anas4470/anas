## نسخة مُصلَّحة - التغييرات الأساسية:
## 1. فك تشفير Base64 قبل إرسال البيانات لـ Gemini (كانت هي سبب الـ "Broken pipe")
## 2. تحديث الموديل من gemini-2.0-flash-exp (قديم/تجريبي) لـ gemini-3.1-flash-live-preview
## 3. إضافة traceback.print_exc() في كل مكان بيمسك استثناء، عشان تشوف السبب الحقيقي وقت أي مشكلة جديدة
## 4. تبسيط حلقة الاستقبال (شيل الـ while True الزيادة اللي كانت لافة حوالين async for)
##
## pip install --upgrade google-genai websockets
import asyncio
import os
import json
import base64
import traceback
import websockets
from google import genai

os.environ.setdefault("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# كان: gemini-2.0-flash-exp (موديل تجريبي قديم)
MODEL = "gemini-3.1-flash-live-preview"

client = genai.Client(
    http_options={
        "api_version": "v1alpha",
    }
)


async def gemini_session_handler(client_websocket):
    print("Mobile Connected!")
    try:
        # أول رسالة المفروض تكون "setup" من الأندرويد (sendInitialSetupMessage)
        # لو معتش أي حاجة أو الشكل غلط، بنكمل بإعداد افتراضي بدل ما نوقع السيرفر
        config = {}
        try:
            config_message = await client_websocket.recv()
            config_data = json.loads(config_message)
            config = config_data.get("setup", {})
        except Exception as e:
            print(f"لم تصل رسالة setup صالحة، هنستخدم إعداد افتراضي: {e}")
            traceback.print_exc()

        if "generation_config" not in config:
            config["generation_config"] = {"response_modalities": ["AUDIO"]}

        config["system_instruction"] = (
            "أنت رفيق، مساعد صوتي لمستخدم كفيف. صف أي صورة توصلك بالتفصيل "
            "وبوضوح، وركّز على العناصر والألوان والمكان والأشخاص إن وجدوا."
        )

        try:
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                print("Connected to Gemini API")

                async def send_to_gemini():
                    try:
                        async for message in client_websocket:
                            try:
                                data = json.loads(message)
                            except json.JSONDecodeError:
                                print("رسالة غير صالحة (مش JSON) - تم تجاهلها")
                                continue

                            if "realtime_input" not in data:
                                continue

                            media_chunks = data["realtime_input"].get("media_chunks", [])
                            for chunk in media_chunks:
                                try:
                                    mime_type = chunk.get("mime_type")
                                    chunk_data = chunk.get("data")
                                    if not mime_type or not chunk_data:
                                        continue

                                    # *** الإصلاح الأساسي ***
                                    # الأندرويد بيبعت الداتا كنص Base64، لكن مكتبة google-genai
                                    # بتستنى بايتات خام (raw bytes). كنا بنبعت النص زي ما هو
                                    # وده كان بيخلي Gemini يرفض الحزمة/يقفل الجلسة فجأة
                                    # وبالتالي "Broken pipe" على أول محاولة إرسال بعدها.
                                    raw_bytes = base64.b64decode(chunk_data)

                                    await session.send(
                                        input={"mime_type": mime_type, "data": raw_bytes}
                                    )
                                    if mime_type == "image/jpeg":
                                        print("تم إرسال صورة لـ Gemini")
                                except Exception as e:
                                    print(f"خطأ أثناء إرسال حزمة لـ Gemini: {e}")
                                    traceback.print_exc()
                    except websockets.exceptions.ConnectionClosed:
                        print("الموبايل قفل الاتصال (إرسال)")
                    except Exception as e:
                        print(f"خطأ عام في send_to_gemini: {e}")
                        traceback.print_exc()
                    finally:
                        print("send_to_gemini closed")

                async def receive_from_gemini():
                    try:
                        async for response in session.receive():
                            if response.server_content is None:
                                continue

                            model_turn = response.server_content.model_turn
                            if model_turn:
                                for part in model_turn.parts:
                                    try:
                                        if getattr(part, "text", None):
                                            await client_websocket.send(
                                                json.dumps({"text": part.text})
                                            )
                                        elif getattr(part, "inline_data", None) is not None:
                                            b64_audio = base64.b64encode(
                                                part.inline_data.data
                                            ).decode("utf-8")
                                            await client_websocket.send(
                                                json.dumps({"audio": b64_audio})
                                            )
                                    except Exception as e:
                                        print(f"خطأ أثناء معالجة part من الرد: {e}")
                                        traceback.print_exc()

                            if response.server_content.turn_complete:
                                print("<Turn complete>")
                    except websockets.exceptions.ConnectionClosedOK:
                        print("الموبايل قفل الاتصال بشكل طبيعي (استقبال)")
                    except Exception as e:
                        print(f"خطأ أثناء الاستقبال من Gemini: {e}")
                        traceback.print_exc()
                    finally:
                        print("Gemini connection closed (receive)")

                send_task = asyncio.create_task(send_to_gemini())
                receive_task = asyncio.create_task(receive_from_gemini())
                await asyncio.gather(send_task, receive_task)

        except Exception as e:
            # هنا بيظهر أي خطأ في فتح الجلسة نفسها مع Gemini
            # (مفتاح API غلط، الموديل مش متاح، quota خلصت، إلخ)
            print(f"فشل فتح/الحفاظ على جلسة Gemini: {e}")
            traceback.print_exc()

    except websockets.exceptions.ConnectionClosed:
        print("Mobile Disconnected (connection closed)")
    except Exception as e:
        print(f"خطأ عام في الـ session: {e}")
        traceback.print_exc()
    finally:
        print("Gemini session closed.")


async def main():
    async with websockets.serve(
        gemini_session_handler, "0.0.0.0", int(os.environ.get("PORT", 8080))
    ):
        print("Running websocket server...")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
