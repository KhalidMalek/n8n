FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt
RUN mkdir -p /app/voices && python -m piper.download_voices --data-dir /app/voices en_US-ljspeech-medium

COPY worker /app/worker
COPY scripts /app/scripts
RUN mkdir -p /app/data /app/secrets

ENV PIPER_MODEL=/app/voices/en_US-ljspeech-medium.onnx
EXPOSE 8000
CMD ["uvicorn", "worker.app:app", "--host", "0.0.0.0", "--port", "8000"]
