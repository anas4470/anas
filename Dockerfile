FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# ريندر سيتكفل بالبورت تلقائياً، وفقط نطلق أمر التشغيل
CMD ["python", "main_for_mobile.py"]