#!/bin/sh
set -eu

CONFIG_PATH="${CHAOXING_BACKEND_CONFIG:-/config/config.yaml}"
RUNTIME_DIR="${CHAOXING_WEB_RUNTIME_DIR:-/data}"
ACCOUNTS_DIR="${CHAOXING_WEB_ACCOUNTS_DIR:-$RUNTIME_DIR/accounts}"
HOST="${CHAOXING_WEB_HOST:-0.0.0.0}"
PORT="${CHAOXING_WEB_PORT:-8000}"

mkdir -p "$(dirname "$CONFIG_PATH")" "$RUNTIME_DIR" "$ACCOUNTS_DIR"

if [ ! -f "$CONFIG_PATH" ]; then
  if [ -f /app/config.yaml ]; then
    cp /app/config.yaml "$CONFIG_PATH"
    echo "[chaoxing] Config file not found, seeded from image config: $CONFIG_PATH"
  else
    cp /app/config.example.yaml "$CONFIG_PATH"
    echo "[chaoxing] Config file not found, created default config at: $CONFIG_PATH"
  fi
fi

python - <<'PY'
from chaoxing.web.settings import get_backend_settings

settings = get_backend_settings()
auth_enabled = bool(settings.admin_username and settings.admin_password)
print(f"[chaoxing] Backend config path: {settings.config_path}")
print(f"[chaoxing] Admin auth enabled: {auth_enabled}")
PY

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn chaoxing.web.app:app --host "$HOST" --port "$PORT"
