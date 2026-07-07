FROM python:3.10-slim

WORKDIR /code

# نسخ ملف المتطلبات وتثبيته
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# تشغيل السيرفر مباشرة
CMD ["python", "main_for_mobile.py"]
