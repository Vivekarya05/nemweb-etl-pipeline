from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_integer_dtype, is_float_dtype

from db import create_schemas, create_unique_index_if_possible, table_exists


def delete_overlapping_rows(engine, schema_name: str, table_name: str, datetime_column: str, start_dt, end_dt, logger) -> int:
    if not table_exists(engine, schema_name, table_name):
        logger.info("Target table %s.%s does not exist yet, so no overlapping rows were deleted", schema_name, table_name)
        return 0

    sql = text(
        f"""
        DELETE FROM {schema_name}.{table_name}
        WHERE {datetime_column} >= :start_dt
          AND {datetime_column} <= :end_dt
        """
    )
    with engine.begin() as connection:
        result = connection.execute(sql, {"start_dt": start_dt, "end_dt": end_dt})
        deleted_rows = int(result.rowcount or 0)
    logger.info("Deleted %s overlapping rows from %s.%s", deleted_rows, schema_name, table_name)
    return deleted_rows


def infer_sql_type_from_series(series: pd.Series) -> str:
    """
    Map pandas dtypes to safe PostgreSQL column types for the raw layer.
    The raw schema should be permissive rather than over-optimised.
    """
    if is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    if is_bool_dtype(series):
        return "BOOLEAN"
    if is_integer_dtype(series):
        return "BIGINT"
    if is_float_dtype(series):
        return "NUMERIC"
    return "TEXT"


def align_table_columns_with_dataframe(engine, schema_name: str, table_name: str, dataframe: pd.DataFrame, logger) -> list[str]:
    """
    Add any missing dataframe columns to an existing table so append loads do not fail.
    This is especially helpful when manual backup tables were created with narrower schemas.
    """
    if not table_exists(engine, schema_name, table_name):
        return []

    existing_columns_query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema_name
          AND table_name = :table_name
        """
    )
    with engine.begin() as connection:
        existing_columns = {
            row[0]
            for row in connection.execute(
                existing_columns_query,
                {"schema_name": schema_name, "table_name": table_name},
            )
        }

    added_columns: list[str] = []
    for column_name in dataframe.columns:
        if column_name in existing_columns:
            continue

        sql_type = infer_sql_type_from_series(dataframe[column_name])
        alter_sql = text(f"ALTER TABLE {schema_name}.{table_name} ADD COLUMN {column_name} {sql_type}")
        with engine.begin() as connection:
            connection.execute(alter_sql)
        added_columns.append(f"{column_name} {sql_type}")
        logger.info(
            "Added missing column %s (%s) to %s.%s",
            column_name,
            sql_type,
            schema_name,
            table_name,
        )

    return added_columns


def load_dataframe_to_database(dataframe: pd.DataFrame, dataset_config: dict, engine, logger) -> dict:
    if dataframe.empty:
        logger.warning("Skipping database load because dataframe is empty")
        return {
            "rows_loaded": 0,
            "table_created": False,
            "overlapping_rows_deleted": 0,
            "unique_index_created": False,
        }

    schema_name = dataset_config["target_schema"]
    table_name = dataset_config["target_table"]
    datetime_column = dataset_config["datetime_column"].lower()
    primary_keys = [primary_key.lower() for primary_key in dataset_config["primary_keys"]]

    create_schemas(engine, logger)
    table_previously_exists = table_exists(engine, schema_name, table_name)
    added_columns = align_table_columns_with_dataframe(engine, schema_name, table_name, dataframe, logger)
    overlapping_rows_deleted = delete_overlapping_rows(
        engine=engine,
        schema_name=schema_name,
        table_name=table_name,
        datetime_column=datetime_column,
        start_dt=dataframe[datetime_column].min(),
        end_dt=dataframe[datetime_column].max(),
        logger=logger,
    )

    dataframe.to_sql(
        name=table_name,
        con=engine,
        schema=schema_name,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    logger.info("Loaded %s rows into %s.%s", len(dataframe), schema_name, table_name)

    unique_index_created = create_unique_index_if_possible(engine, schema_name, table_name, primary_keys, logger)
    return {
        "rows_loaded": int(len(dataframe)),
        "table_created": not table_previously_exists,
        "overlapping_rows_deleted": overlapping_rows_deleted,
        "unique_index_created": unique_index_created,
        "added_columns": added_columns,
    }
