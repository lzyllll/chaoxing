#!/bin/sh
set -eu

CONFIG_PATH="${CHAOXING_BACKEND_CONFIG:-/config/config.yaml}"
RUNTIME_DIR="${CHAOXING_WEB_RUNTIME_DIR:-/data}"
ACCOUNTS_DIR="${CHAOXING_WEB_ACCOUNTS_DIR:-$RUNTIME_DIR/accounts}"
HOST="${CHAOXING_WEB_HOST:-0.0.0.0}"
PORT="${CHAOXING_WEB_PORT:-8000}"

mkdir -p "$(dirname "$CONFIG_PATH")" "$RUNTIME_DIR" "$ACCOUNTS_DIR"

if [ ! -f "$CONFIG_PATH" ]; then
  cp /app/config.example.yaml "$CONFIG_PATH"
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn chaoxing.web.app:app --host "$HOST" --port "$PORT"
