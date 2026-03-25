# -*- coding: utf-8 -*-
import configparser
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKEND_CONFIG_PATH = PROJECT_ROOT / "backend.ini"
DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_path(value: str | None, *, base_dir: Path, default: Path) -> Path:
    if not value:
        return default.resolve()

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _get_option(
    parser: configparser.ConfigParser,
    *,
    section: str,
    option: str,
    env_name: str,
    default: str | None = None,
) -> str | None:
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip():
        return env_value.strip()

    if parser.has_option(section, option):
        return parser.get(section, option).strip()

    return default


def resolve_backend_config_path(config_path: str | Path | None = None) -> Path:
    raw_path = config_path or os.getenv("CHAOXING_BACKEND_CONFIG")
    if not raw_path:
        return DEFAULT_BACKEND_CONFIG_PATH

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_backend_config(config_path: str | Path | None = None) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    resolved_path = resolve_backend_config_path(config_path)
    if resolved_path.is_file():
        parser.read(resolved_path, encoding="utf8")
    return parser


@dataclass(frozen=True, slots=True)
class BackendSettings:
    config_path: Path
    server_host: str
    server_port: int
    server_reload: bool
    cors_origins: list[str]
    runtime_dir: Path
    database_path: Path
    accounts_dir: Path


@lru_cache(maxsize=1)
def get_backend_settings() -> BackendSettings:
    config_path = resolve_backend_config_path()
    parser = load_backend_config(config_path)
    base_dir = config_path.parent

    server_host = _get_option(
        parser,
        section="server",
        option="host",
        env_name="CHAOXING_WEB_HOST",
        default="127.0.0.1",
    ) or "127.0.0.1"
    server_port_raw = _get_option(
        parser,
        section="server",
        option="port",
        env_name="CHAOXING_WEB_PORT",
        default="8000",
    ) or "8000"
    server_reload = _to_bool(
        _get_option(
            parser,
            section="server",
            option="reload",
            env_name="CHAOXING_WEB_RELOAD",
            default="true",
        ),
        default=True,
    )
    cors_origins = _split_csv(
        _get_option(
            parser,
            section="server",
            option="cors_origins",
            env_name="CHAOXING_WEB_CORS_ORIGINS",
            default=",".join(DEFAULT_CORS_ORIGINS),
        )
    )

    try:
        server_port = int(server_port_raw)
    except ValueError:
        server_port = 8000

    runtime_dir = _resolve_path(
        _get_option(
            parser,
            section="storage",
            option="runtime_dir",
            env_name="CHAOXING_WEB_RUNTIME_DIR",
            default=".runtime",
        ),
        base_dir=base_dir,
        default=PROJECT_ROOT / ".runtime",
    )
    database_path = _resolve_path(
        _get_option(
            parser,
            section="storage",
            option="database_path",
            env_name="CHAOXING_WEB_DATABASE_PATH",
        ),
        base_dir=base_dir,
        default=runtime_dir / "chaoxing-web.sqlite3",
    )
    accounts_dir = _resolve_path(
        _get_option(
            parser,
            section="storage",
            option="accounts_dir",
            env_name="CHAOXING_WEB_ACCOUNTS_DIR",
        ),
        base_dir=base_dir,
        default=runtime_dir / "accounts",
    )

    return BackendSettings(
        config_path=config_path,
        server_host=server_host,
        server_port=server_port,
        server_reload=server_reload,
        cors_origins=cors_origins or list(DEFAULT_CORS_ORIGINS),
        runtime_dir=runtime_dir,
        database_path=database_path,
        accounts_dir=accounts_dir,
    )


def default_account_cookies_path(username: str) -> Path:
    return get_backend_settings().accounts_dir / f"{username}.json"


__all__ = [
    "BackendSettings",
    "DEFAULT_BACKEND_CONFIG_PATH",
    "default_account_cookies_path",
    "get_backend_settings",
    "load_backend_config",
    "resolve_backend_config_path",
]
