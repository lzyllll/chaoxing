# -*- coding: utf-8 -*-
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from chaoxing.web import models  # noqa: F401

RUNTIME_DIR = Path(".runtime")
DB_PATH = RUNTIME_DIR / "chaoxing-web.sqlite3"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    (RUNTIME_DIR / "accounts").mkdir(parents=True, exist_ok=True)


def create_db_and_tables() -> None:
    ensure_runtime_dirs()
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    create_db_and_tables()
    return Session(engine)
