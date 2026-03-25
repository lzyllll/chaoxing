FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_HTTP_TIMEOUT=180 \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        build-essential \
        ca-certificates \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml requirements.txt uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project \
    && find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} + \
    && find /opt/venv -type f -name "*.pyc" -delete \
    && find /opt/venv -type d -name "tests" -prune -exec rm -rf {} + \
    && find /opt/venv -type d -name "test" -prune -exec rm -rf {} + \
    && find /opt/venv -type d -name "testing" -prune -exec rm -rf {} + \
    && (find /opt/venv -type f -name "*.so" -exec strip --strip-unneeded {} + || true) \
    && rm -rf /root/.cache /tmp/*

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    VIRTUAL_ENV=/opt/venv \
    CHAOXING_WEB_HOST=0.0.0.0 \
    CHAOXING_WEB_PORT=8000 \
    CHAOXING_WEB_RELOAD=false \
    CHAOXING_WEB_RUNTIME_DIR=/data \
    CHAOXING_WEB_DATABASE_PATH=/data/chaoxing-web.sqlite3 \
    CHAOXING_WEB_ACCOUNTS_DIR=/data/accounts

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libffi8 \
        libgcc-s1 \
        libstdc++6 \
        libxml2 \
        libxslt1.1 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY chaoxing ./chaoxing
COPY resource ./resource
COPY web_api.py ./
COPY backend.example.ini ./

RUN mkdir -p /data/accounts /config

EXPOSE 8000

CMD ["python", "web_api.py"]
