from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from utils import serialise_datetime


DEFAULT_SCHEMAS = ["raw", "staging", "analytics"]


def load_database_settings() -> dict:
    load_dotenv()
    return {
        "db_type": os.getenv("DB_TYPE", "postgresql"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "name": os.getenv("DB_NAME", "nemweb"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "your_password"),
    }


def build_connection_url() -> str:
    settings = load_database_settings()
    return (
        f"{settings['db_type']}+psycopg2://{settings['user']}:{settings['password']}"
        f"@{settings['host']}:{settings['port']}/{settings['name']}"
    )


def get_engine():
    return create_engine(build_connection_url(), future=True)


def test_database_connection() -> dict:
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        settings = load_database_settings()
        return {
            "ok": True,
            "message": f"Connected to {settings['name']} on {settings['host']}:{settings['port']}.",
        }
    except SQLAlchemyError as exc:
        return {"ok": False, "message": str(exc)}


def create_schemas(engine, logger) -> None:
    with engine.begin() as connection:
        for schema_name in DEFAULT_SCHEMAS:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            logger.info("Ensured schema exists: %s", schema_name)


def table_exists(engine, schema_name: str, table_name: str) -> bool:
    return inspect(engine).has_table(table_name, schema=schema_name)


def unique_index_name(schema_name: str, table_name: str, primary_keys: list[str]) -> str:
    key_suffix = "_".join(primary_keys)
    return f"ux_{schema_name}_{table_name}_{key_suffix}"


def create_unique_index_if_possible(engine, schema_name: str, table_name: str, primary_keys: list[str], logger) -> bool:
    if not primary_keys:
        return False

    if not table_exists(engine, schema_name, table_name):
        return False

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns(table_name, schema=schema_name)}
    if not all(primary_key in columns for primary_key in primary_keys):
        logger.warning(
            "Skipping unique index creation for %s.%s because not all primary key columns exist",
            schema_name,
            table_name,
        )
        return False

    index_name = unique_index_name(schema_name, table_name, primary_keys)
    primary_key_sql = ", ".join(primary_keys)
    sql = text(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
        ON {schema_name}.{table_name} ({primary_key_sql})
        """
    )
    with engine.begin() as connection:
        connection.execute(sql)
    logger.info("Ensured unique index exists: %s", index_name)
    return True


def get_existing_data_status(engine, schema_name: str, table_name: str, datetime_column: str, start_dt, end_dt) -> dict:
    if not table_exists(engine, schema_name, table_name):
        return {
            "table_exists": False,
            "rows_in_range": 0,
            "min_datetime": None,
            "max_datetime": None,
            "already_loaded": False,
            "status_message": "Target table does not exist yet.",
        }

    sql = text(
        f"""
        SELECT
            COUNT(*) AS rows_in_range,
            MIN({datetime_column}) AS min_datetime,
            MAX({datetime_column}) AS max_datetime
        FROM {schema_name}.{table_name}
        WHERE {datetime_column} >= :start_dt
          AND {datetime_column} <= :end_dt
        """
    )

    with engine.begin() as connection:
        row = connection.execute(sql, {"start_dt": start_dt, "end_dt": end_dt}).mappings().one()

    rows_in_range = int(row["rows_in_range"] or 0)
    min_datetime = row["min_datetime"]
    max_datetime = row["max_datetime"]
    already_loaded = (
        rows_in_range > 0
        and min_datetime is not None
        and max_datetime is not None
        and min_datetime <= start_dt
        and max_datetime >= end_dt
    )
    partial_overlap = rows_in_range > 0 and not already_loaded

    if already_loaded:
        status_message = "Data already exists for this selected period. No duplicate load performed."
    elif partial_overlap:
        status_message = "Partial overlap exists. Overlapping rows will be deleted and reloaded cleanly."
    else:
        status_message = "No existing rows were found for the selected period."

    return {
        "table_exists": True,
        "rows_in_range": rows_in_range,
        "min_datetime": min_datetime,
        "max_datetime": max_datetime,
        "already_loaded": already_loaded,
        "partial_overlap": partial_overlap,
        "status_message": status_message,
    }


def describe_existing_status(existing_status: dict) -> dict:
    return {
        "table_exists": existing_status.get("table_exists", False),
        "rows_in_range": int(existing_status.get("rows_in_range", 0) or 0),
        "min_datetime": serialise_datetime(existing_status.get("min_datetime")),
        "max_datetime": serialise_datetime(existing_status.get("max_datetime")),
        "already_loaded": bool(existing_status.get("already_loaded", False)),
        "partial_overlap": bool(existing_status.get("partial_overlap", False)),
        "status_message": existing_status.get("status_message", ""),
    }


def run_test_table_insert() -> dict:
    """
    Write a small row into analytics.pipeline_healthcheck so we can prove that
    the web app and SQLAlchemy can write to PostgreSQL even when NEMWeb rows
    are not loading yet.
    """
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS analytics.pipeline_healthcheck (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO analytics.pipeline_healthcheck (created_at, status, note)
                VALUES (:created_at, :status, :note)
                """
            ),
            {
                "created_at": datetime.utcnow(),
                "status": "ok",
                "note": "Manual dashboard test insert",
            },
        )
        row_count = connection.execute(text("SELECT COUNT(*) FROM analytics.pipeline_healthcheck")).scalar_one()
    return {
        "ok": True,
        "message": f"Test table insert succeeded. analytics.pipeline_healthcheck now has {row_count} rows.",
        "table_name": "analytics.pipeline_healthcheck",
        "row_count": int(row_count),
    }
