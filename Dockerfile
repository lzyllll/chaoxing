FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

COPY chaoxing ./chaoxing
COPY resource ./resource
COPY backend.example.ini ./backend.example.ini
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY LICENSE ./LICENSE

RUN mkdir -p /config /data/accounts

ENV CHAOXING_BACKEND_CONFIG=/config/backend.ini \
    CHAOXING_WEB_HOST=0.0.0.0 \
    CHAOXING_WEB_PORT=8000 \
    CHAOXING_WEB_RELOAD=false \
    CHAOXING_WEB_RUNTIME_DIR=/data \
    CHAOXING_WEB_DATABASE_PATH=/data/chaoxing-web.sqlite3 \
    CHAOXING_WEB_ACCOUNTS_DIR=/data/accounts

VOLUME ["/config", "/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3); sys.exit(0)"

CMD ["uvicorn", "chaoxing.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
