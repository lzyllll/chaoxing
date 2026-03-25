FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CHAOXING_BACKEND_CONFIG=/config/backend.ini \
    CHAOXING_WEB_HOST=0.0.0.0 \
    CHAOXING_WEB_PORT=8000 \
    CHAOXING_WEB_RELOAD=false \
    CHAOXING_WEB_RUNTIME_DIR=/data \
    CHAOXING_WEB_DATABASE_PATH=/data/chaoxing-web.sqlite3 \
    CHAOXING_WEB_ACCOUNTS_DIR=/data/accounts

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p /config /data \
    && cp backend.example.ini /config/backend.ini

VOLUME ["/config", "/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"

CMD ["python", "web_api.py"]
