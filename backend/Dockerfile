# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instala solo FastAPI, Uvicorn y el CLIENTE HTTP de Chroma
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
