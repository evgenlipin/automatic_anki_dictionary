# В образе только зависимости: код монтируется из compose, пересборка нужна лишь при смене requirements.txt
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANKI_WORKSPACE=/workspace

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "-m", "anki_dict"]
