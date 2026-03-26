FROM python:3.11-slim

LABEL maintainer="AirSense+"
LABEL description="AirSense+ FastAPI backend for hardware-aligned AQI prediction"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"PORT\", \"8000\")}/').read()" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
