#!/usr/bin/env python3
"""
One-time migration: copy all tables and data from PostgreSQL to MySQL.

Usage:
  python scripts/migrate_postgres_to_mysql.py

Environment (optional overrides for source PostgreSQL):
  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Target MySQL uses app.config.settings (DB_* in .env).
"""

from __future__ import annotations

import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config.settings import settings  # noqa: E402
from app.database.base_class import Base  # noqa: E402

# Import models so metadata is populated
from app.modules.auth.models.user import User  # noqa: F401,E402
from app.modules.auth.models.otp import OTPVerification  # noqa: F401,E402
from app.modules.auth.models.password_reset import PasswordResetToken  # noqa: F401,E402
from app.modules.onboarding.models.onboarding import OnboardingProgress  # noqa: E402
from app.modules.proz.models.proz import (  # noqa: F401,E402
    ProzProfile,
    ProzSpecialty,
    Review,
    Specialty,
)
from app.modules.tasks.models.task import (  # noqa: F401,E402
    ServiceRequest,
    TaskAssignment,
    TaskNotification,
)

TABLE_ORDER = [
    "users",
    "otp_verifications",
    "password_reset_tokens",
    "onboarding_progress",
    "proz_profiles",
    "specialties",
    "proz_specialty",
    "reviews",
    "service_requests",
    "task_assignments",
    "task_notifications",
]


def _postgres_url() -> str:
    from urllib.parse import quote_plus
    import os

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "prozlab_db")
    user = os.getenv("POSTGRES_USER", "proz_user")
    password = os.getenv("POSTGRES_PASSWORD", "Root#2022")
    return (
        f"postgresql+psycopg2://{user}:{quote_plus(password)}"
        f"@{host}:{port}/{db}"
    )


def _mysql_server_url() -> str:
    from urllib.parse import quote_plus

    password = quote_plus(settings.DB_PASSWORD)
    return (
        f"mysql+pymysql://{settings.DB_USER}:{password}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/?charset=utf8mb4"
    )


def _mysql_db_url() -> str:
    return settings.get_database_url


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "value"):  # enum
        return value.value
    return value


def _ensure_mysql_database(server_engine: Engine) -> None:
    db_name = settings.DB_NAME
    with server_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()


def _existing_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _copy_table(pg_engine: Engine, mysql_engine: Engine, table: str) -> int:
    pg_inspector = inspect(pg_engine)
    if table not in pg_inspector.get_table_names():
        print(f"  skip {table} (not in source)")
        return 0

    columns = [col["name"] for col in pg_inspector.get_columns(table)]
    col_list = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    insert_sql = text(f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})")

    with pg_engine.connect() as pg_conn:
        rows = pg_conn.execute(text(f'SELECT * FROM "{table}"')).mappings().all()

    if not rows:
        print(f"  {table}: 0 rows")
        return 0

    with mysql_engine.begin() as mysql_conn:
        mysql_conn.execute(text(f"DELETE FROM `{table}`"))
        for row in rows:
            payload: Dict[str, Any] = {
                col: _normalize_value(row[col]) for col in columns
            }
            mysql_conn.execute(insert_sql, payload)

    print(f"  {table}: {len(rows)} rows")
    return len(rows)


def main() -> int:
    print("Source PostgreSQL:", _postgres_url().replace("Root%232022", "***"))
    print("Target MySQL:", _mysql_db_url().replace("KBLWin%21", "***"))

    pg_engine = create_engine(_postgres_url(), pool_pre_ping=True)
    server_engine = create_engine(_mysql_server_url(), pool_pre_ping=True, isolation_level="AUTOCOMMIT")

    print("\nCreating MySQL database if needed...")
    _ensure_mysql_database(server_engine)

    mysql_engine = create_engine(_mysql_db_url(), pool_pre_ping=True)

    print("Creating MySQL tables from SQLAlchemy models...")
    Base.metadata.drop_all(bind=mysql_engine)
    Base.metadata.create_all(bind=mysql_engine)

    print("\nCopying data (FK order)...")
    total = 0
    for table in TABLE_ORDER:
        total += _copy_table(pg_engine, mysql_engine, table)

    print(f"\nDone. Migrated {total} rows across {len(TABLE_ORDER)} tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
