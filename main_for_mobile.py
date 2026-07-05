import asyncio
import os
import json
import base64
import websockets
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL = "gemini-2.0-flash-exp"

# response_modalities=["AUDIO"] يخلي الموديل يرد بصوت فعلي بدل نص بس.
# output_audio_transcription بيدّيك كمان نص (transcript) للصوت اللي الموديل بيقوله،
# عشان تقدر تعرضه في الـ chatLog في نفس الوقت اللي بيتشغل فيه الصوت.
LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription=types.AudioTranscriptionConfig(),
)


async def handler(websocket):
    print("Mobile Connected!")
    try:
        async with client.aio.live.connect(model=MODEL, config=LIVE_CONFIG) as session:

            async def listen_to_mobile():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        print("رسالة غير صالحة (مش JSON) - تم تجاهلها")
                        continue

                    if "realtime_input" not in data:
                        print(f"رسالة بدون realtime_input - تم تجاهلها: {list(data.keys())}")
                        continue

                    realtime_input = data["realtime_input"]
                    mime_type = realtime_input.get("mime_type", "")

                    try:
                        await session.send(input=realtime_input)

                        # الصورة لوحدها مفيهاش "صمت" يخلي الموديل يحس إن الدور خلص
                        # (زي الصوت اللي بيعتمد على VAD)، فلازم نجبره صراحة إنه يرد
                        # فور ما توصله صورة، عشان يوصفها بصوت للمستخدم كفيف
                        if mime_type.startswith("image/"):
                            await session.send(
                                input="صف الصورة دي بالتفصيل وبوضوح لشخص مكفوف، "
                                      "ركّز على أهم العناصر والألوان والمكان.",
                                end_of_turn=True,
                            )
                    except Exception as e:
                        # أي خطأ هنا (زي شكل بيانات غلط) ميقفلش السوكيت بشكل مفاجئ (Broken pipe)
                        # من غير ما نعرف السبب - بنسجله ونكمل
                        print("خطأ أثناء إرسال البيانات لـ Gemini:", e)

            async def send_to_mobile():
                async for response in session.receive():
                    try:
                        # نص أو صوت جاي مباشرة (الـ API بيدّي alias مختصر response.text / response.data)
                        if response.text:
                            await websocket.send(json.dumps({"text": response.text}))

                        if response.data:
                            audio_b64 = base64.b64encode(response.data).decode("utf-8")
                            await websocket.send(json.dumps({"audio": audio_b64}))

                        # نفس المحتوى لكن عن طريق server_content (احتياطي لو الـ alias مش متاح)
                        server_content = response.server_content
                        if server_content:
                            if server_content.model_turn:
                                for part in server_content.model_turn.parts:
                                    if part.text:
                                        await websocket.send(json.dumps({"text": part.text}))
                                    if part.inline_data and part.inline_data.data:
                                        audio_b64 = base64.b64encode(
                                            part.inline_data.data
                                        ).decode("utf-8")
                                        await websocket.send(json.dumps({"audio": audio_b64}))

                            # نص تفريغ (transcript) الصوت اللي الموديل قاله
                            if getattr(server_content, "output_transcription", None):
                                transcript = server_content.output_transcription.text
                                if transcript:
                                    await websocket.send(json.dumps({"text": transcript}))

                    except websockets.exceptions.ConnectionClosed:
                        print("الموبايل قفل الاتصال أثناء إرسال الرد")
                        return
                    except Exception as e:
                        print("خطأ أثناء إرسال الرد للموبايل:", e)

            await asyncio.gather(listen_to_mobile(), send_to_mobile())

    except websockets.exceptions.ConnectionClosed:
        print("Mobile Disconnected (connection closed)")
    except Exception as e:
        print("خطأ عام في الـ handler:", e)
    finally:
        print("Session ended")


async def main():
    async with websockets.serve(handler, "0.0.0.0", int(os.environ.get("PORT", 8080))):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
