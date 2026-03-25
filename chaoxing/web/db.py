# -*- coding: utf-8 -*-
import sqlite3

from sqlmodel import SQLModel, Session, create_engine

from chaoxing.web import models  # noqa: F401
from chaoxing.web.settings import get_backend_settings

SETTINGS = get_backend_settings()
RUNTIME_DIR = SETTINGS.runtime_dir
DB_PATH = SETTINGS.database_path
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS.accounts_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def create_db_and_tables() -> None:
    ensure_runtime_dirs()
    SQLModel.metadata.create_all(engine)
    migrate_sqlite_schema()


def get_session() -> Session:
    create_db_and_tables()
    return Session(engine)


def migrate_sqlite_schema() -> None:
    answer_record_table = models.AnswerRecord.__table__.name
    answer_record_columns = {
        "course_title": "TEXT NOT NULL DEFAULT ''",
        "chapter_title": "TEXT NOT NULL DEFAULT ''",
    }

    with sqlite3.connect(DB_PATH) as connection:
        existing_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if answer_record_table not in existing_tables:
            return

        existing_columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info('{answer_record_table}')")
        }
        for column_name, definition in answer_record_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                f"ALTER TABLE {answer_record_table} ADD COLUMN {column_name} {definition}"
            )
        connection.commit()
