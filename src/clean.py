from __future__ import annotations

import pandas as pd

from utils import coerce_numeric_columns, normalise_column_name, safe_to_datetime


def project_standard_columns(cleaned: pd.DataFrame, dataset_config: dict, logger) -> pd.DataFrame:
    """
    Keep a stable subset of business-friendly columns for the raw load.
    This avoids pushing every exotic NEMWeb column into PostgreSQL at the start.
    """
    standard_columns = dataset_config.get("standard_columns") or []
    if not standard_columns:
        return cleaned

    normalised_standard_columns = [normalise_column_name(column) for column in standard_columns]
    available_columns = [column for column in normalised_standard_columns if column in cleaned.columns]
    missing_columns = [column for column in normalised_standard_columns if column not in cleaned.columns]

    if missing_columns:
        logger.info(
            "Standard columns missing for %s and skipped from projection: %s",
            dataset_config.get("target_table", "dataset"),
            ", ".join(missing_columns),
        )

    if available_columns:
        logger.info(
            "Projecting %s standard columns for %s",
            len(available_columns),
            dataset_config.get("target_table", "dataset"),
        )
        return cleaned[available_columns].copy()

    return cleaned


def clean_dataframe(dataframe: pd.DataFrame, dataset_config: dict, start_dt, end_dt, logger) -> pd.DataFrame:
    """Standardise column names and tidy the parsed dataset."""
    if dataframe.empty:
        return dataframe

    cleaned = dataframe.copy()
    cleaned.columns = [normalise_column_name(column) for column in cleaned.columns]

    for column in cleaned.columns:
        if cleaned[column].dtype == object:
            cleaned[column] = cleaned[column].astype(str).str.strip()
            cleaned[column] = cleaned[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    cleaned = cleaned.dropna(how="all")
    cleaned = cleaned.drop_duplicates()

    datetime_column = normalise_column_name(dataset_config["datetime_column"])
    if datetime_column in cleaned.columns:
        cleaned[datetime_column] = safe_to_datetime(cleaned[datetime_column])
        cleaned = cleaned[cleaned[datetime_column].notna()]
        cleaned = cleaned[
            (cleaned[datetime_column] >= start_dt) &
            (cleaned[datetime_column] <= end_dt)
        ]

    if "regionid" in cleaned.columns:
        cleaned["regionid"] = cleaned["regionid"].astype(str).str.upper().str.strip()

    cleaned = coerce_numeric_columns(cleaned, exclude=[datetime_column, "regionid", "intervention"])
    cleaned = project_standard_columns(cleaned, dataset_config, logger)

    primary_keys = [normalise_column_name(key) for key in dataset_config.get("primary_keys", [])]
    available_primary_keys = [key for key in primary_keys if key in cleaned.columns]
    if available_primary_keys:
        before_dedup = len(cleaned)
        cleaned = cleaned.drop_duplicates(subset=available_primary_keys)
        removed_rows = before_dedup - len(cleaned)
        if removed_rows > 0:
            logger.info(
                "Removed %s duplicate rows using primary keys for %s",
                removed_rows,
                dataset_config.get("target_table", "dataset"),
            )

    cleaned = cleaned.reset_index(drop=True)
    logger.info("Cleaned dataframe to %s rows", len(cleaned))
    return cleaned
