# -*- coding: utf-8 -*-
import os.path
from pathlib import Path

import requests

from chaoxing.core.config import GlobalConst as gc


def save_cookies(session: requests.Session, path: str | None = None):
    cookie_path = Path(path or gc.COOKIES_PATH)
    cookie_path.parent.mkdir(parents=True, exist_ok=True)

    buffer=""
    with cookie_path.open("w", encoding="utf8") as f:
        for k, v in session.cookies.items():
            buffer += f"{k}={v};"
        buffer = buffer.removesuffix(";")
        f.write(buffer)


def use_cookies(path: str | None = None) -> dict:
    cookie_path = Path(path or gc.COOKIES_PATH)
    if not os.path.exists(cookie_path):
        return {}

    cookies={}
    with cookie_path.open("r", encoding="utf8") as f:
        buffer = f.read().strip()
        if not buffer:
            return {}
        for item in buffer.split(";"):
            k, v = item.strip().split("=")
            cookies[k] = v

    return cookies
