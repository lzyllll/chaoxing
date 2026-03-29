FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY pyproject.toml ./pyproject.toml

COPY chaoxing ./chaoxing
COPY resource ./resource
COPY README.md ./README.md
COPY LICENSE ./LICENSE

RUN uv sync --no-dev

RUN mkdir -p /config /data/accounts

ENV CHAOXING_BACKEND_CONFIG=/config/config.yaml \
    CHAOXING_WEB_HOST=0.0.0.0 \
    CHAOXING_WEB_PORT=8000 \
    CHAOXING_WEB_RELOAD=false \
    CHAOXING_WEB_RUNTIME_DIR=/data \
    CHAOXING_WEB_DATABASE_PATH=/data/chaoxing-web.sqlite3 \
    CHAOXING_WEB_ACCOUNTS_DIR=/data/accounts

VOLUME ["/config", "/data"]

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "-m", "uvicorn", "chaoxing.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
