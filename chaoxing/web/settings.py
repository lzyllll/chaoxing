# -*- coding: utf-8 -*-
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKEND_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
DEFAULT_TIKU_TRUE_LIST = ["正确", "对", "true", "是"]
DEFAULT_TIKU_FALSE_LIST = ["错误", "错", "false", "否"]
DEFAULT_BACKEND_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "reload": True,
        "cors_origins": list(DEFAULT_CORS_ORIGINS),
    },
    "storage": {
        "runtime_dir": ".runtime",
        "database_path": ".runtime/chaoxing-web.sqlite3",
        "accounts_dir": ".runtime/accounts",
    },
    "admin": {
        "username": "",
        "password": "",
    },
    "tiku": {
        "provider": "",
        "submit": False,
        "cover_rate": 0.7,
        "true_list": list(DEFAULT_TIKU_TRUE_LIST),
        "false_list": list(DEFAULT_TIKU_FALSE_LIST),
        "delay": 0,
        "tokens": "",
        "url": "",
        "endpoint": "",
        "key": "",
        "model": "",
        "http_proxy": "",
        "min_interval_seconds": 3,
        "siliconflow_endpoint": "https://api.siliconflow.cn/v1/chat/completions",
        "siliconflow_key": "",
        "siliconflow_model": "deepseek-ai/DeepSeek-V3",
    },
    "notification": {
        "provider": "",
        "url": "",
        "tg_chat_id": "",
    },
}


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return _split_csv(value)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _to_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _resolve_path(value: Any, *, base_dir: Path, default: Path) -> Path:
    raw_value = _as_string(value)
    if not raw_value:
        return default.resolve()

    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _get_section(config: Mapping[str, Any], section: str) -> dict[str, Any]:
    section_value = config.get(section)
    if isinstance(section_value, Mapping):
        return dict(section_value)
    return {}


def _get_option(
    config: Mapping[str, Any],
    *,
    section: str,
    option: str,
    env_name: str,
    default: Any = None,
) -> Any:
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip():
        return env_value.strip()
    return _get_section(config, section).get(option, default)


def normalize_backend_tiku_config(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = dict(payload) if isinstance(payload, Mapping) else {}

    if "provider" in normalized:
        normalized["provider"] = _as_string(normalized.get("provider"))
    if "submit" in normalized:
        normalized["submit"] = "true" if _to_bool(normalized.get("submit"), False) else "false"
    if "cover_rate" in normalized:
        normalized["cover_rate"] = _as_string(
            normalized.get("cover_rate"),
            str(DEFAULT_BACKEND_CONFIG["tiku"]["cover_rate"]),
        )
    if "true_list" in normalized:
        true_list = _as_string_list(normalized.get("true_list"))
        normalized["true_list"] = ",".join(true_list or list(DEFAULT_TIKU_TRUE_LIST))
    if "false_list" in normalized:
        false_list = _as_string_list(normalized.get("false_list"))
        normalized["false_list"] = ",".join(false_list or list(DEFAULT_TIKU_FALSE_LIST))

    return normalized


def resolve_backend_config_path(config_path: str | Path | None = None) -> Path:
    raw_path = config_path or os.getenv("CHAOXING_BACKEND_CONFIG")
    if not raw_path:
        return DEFAULT_BACKEND_CONFIG_PATH

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_backend_config(config_path: str | Path | None = None) -> dict[str, Any]:
    resolved_path = resolve_backend_config_path(config_path)
    if not resolved_path.is_file():
        return {}

    try:
        with resolved_path.open("r", encoding="utf8") as file:
            loaded = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid backend config YAML: {resolved_path}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, Mapping):
        raise ValueError(f"Backend config root must be a mapping: {resolved_path}")
    return dict(loaded)


def load_backend_tiku_config(config_path: str | Path | None = None) -> dict[str, Any]:
    config = load_backend_config(config_path)
    return normalize_backend_tiku_config(_get_section(config, "tiku"))


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
    admin_username: str
    admin_password: str


@lru_cache(maxsize=1)
def get_backend_settings() -> BackendSettings:
    config_path = resolve_backend_config_path()
    config = load_backend_config(config_path)
    base_dir = config_path.parent

    server_host = _as_string(
        _get_option(
            config,
            section="server",
            option="host",
            env_name="CHAOXING_WEB_HOST",
            default=DEFAULT_BACKEND_CONFIG["server"]["host"],
        ),
        DEFAULT_BACKEND_CONFIG["server"]["host"],
    )
    server_port = _to_int(
        _get_option(
            config,
            section="server",
            option="port",
            env_name="CHAOXING_WEB_PORT",
            default=DEFAULT_BACKEND_CONFIG["server"]["port"],
        ),
        int(DEFAULT_BACKEND_CONFIG["server"]["port"]),
    )
    server_reload = _to_bool(
        _get_option(
            config,
            section="server",
            option="reload",
            env_name="CHAOXING_WEB_RELOAD",
            default=DEFAULT_BACKEND_CONFIG["server"]["reload"],
        ),
        bool(DEFAULT_BACKEND_CONFIG["server"]["reload"]),
    )
    cors_origins = _as_string_list(
        _get_option(
            config,
            section="server",
            option="cors_origins",
            env_name="CHAOXING_WEB_CORS_ORIGINS",
            default=list(DEFAULT_CORS_ORIGINS),
        )
    )

    runtime_dir = _resolve_path(
        _get_option(
            config,
            section="storage",
            option="runtime_dir",
            env_name="CHAOXING_WEB_RUNTIME_DIR",
            default=DEFAULT_BACKEND_CONFIG["storage"]["runtime_dir"],
        ),
        base_dir=base_dir,
        default=PROJECT_ROOT / ".runtime",
    )
    database_path = _resolve_path(
        _get_option(
            config,
            section="storage",
            option="database_path",
            env_name="CHAOXING_WEB_DATABASE_PATH",
            default=DEFAULT_BACKEND_CONFIG["storage"]["database_path"],
        ),
        base_dir=base_dir,
        default=runtime_dir / "chaoxing-web.sqlite3",
    )
    accounts_dir = _resolve_path(
        _get_option(
            config,
            section="storage",
            option="accounts_dir",
            env_name="CHAOXING_WEB_ACCOUNTS_DIR",
            default=DEFAULT_BACKEND_CONFIG["storage"]["accounts_dir"],
        ),
        base_dir=base_dir,
        default=runtime_dir / "accounts",
    )
    admin_username = _as_string(
        _get_option(
            config,
            section="admin",
            option="username",
            env_name="CHAOXING_WEB_ADMIN_USERNAME",
            default=DEFAULT_BACKEND_CONFIG["admin"]["username"],
        )
    )
    admin_password = _as_string(
        _get_option(
            config,
            section="admin",
            option="password",
            env_name="CHAOXING_WEB_ADMIN_PASSWORD",
            default=DEFAULT_BACKEND_CONFIG["admin"]["password"],
        )
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
        admin_username=admin_username,
        admin_password=admin_password,
    )


def default_account_cookies_path(username: str) -> Path:
    return get_backend_settings().accounts_dir / f"{username}.json"


__all__ = [
    "BackendSettings",
    "DEFAULT_BACKEND_CONFIG",
    "DEFAULT_BACKEND_CONFIG_PATH",
    "default_account_cookies_path",
    "get_backend_settings",
    "load_backend_config",
    "load_backend_tiku_config",
    "normalize_backend_tiku_config",
    "resolve_backend_config_path",
]
