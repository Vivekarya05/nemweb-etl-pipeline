from __future__ import annotations

import pandas as pd

from utils import serialise_datetime


def validate_dataframe(dataframe: pd.DataFrame, dataset_config: dict, logger) -> bool:
    """Run lightweight validation checks and log useful diagnostics."""
    dataset_name = dataset_config["target_table"]
    datetime_column = dataset_config["datetime_column"].lower()
    primary_keys = [key.lower() for key in dataset_config["primary_keys"]]

    if dataframe.empty:
        logger.error("Validation failed for %s because the dataframe is empty", dataset_name)
        return False

    if datetime_column not in dataframe.columns:
        logger.error("Validation failed for %s because %s is missing", dataset_name, datetime_column)
        return False

    missing_datetime_count = int(dataframe[datetime_column].isna().sum())
    if missing_datetime_count > 0:
        logger.error(
            "Validation failed for %s because %s rows have missing %s values",
            dataset_name,
            missing_datetime_count,
            datetime_column,
        )
        return False

    missing_primary_keys = [key for key in primary_keys if key not in dataframe.columns]
    if missing_primary_keys:
        logger.error(
            "Validation failed for %s because primary key columns are missing: %s",
            dataset_name,
            ", ".join(missing_primary_keys),
        )
        return False

    duplicate_key_count = int(dataframe.duplicated(subset=primary_keys).sum())
    if duplicate_key_count > 0:
        logger.error(
            "Validation failed for %s because %s duplicate primary keys were found",
            dataset_name,
            duplicate_key_count,
        )
        return False

    min_datetime = dataframe[datetime_column].min()
    max_datetime = dataframe[datetime_column].max()
    logger.info(
        "Validation passed for %s | rows=%s | min_datetime=%s | max_datetime=%s",
        dataset_name,
        len(dataframe),
        serialise_datetime(min_datetime),
        serialise_datetime(max_datetime),
    )
    return True
