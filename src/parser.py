from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from utils import normalise_column_name, table_name_matches


def logical_table_name_from_row(row: list[str]) -> str:
    if len(row) < 3:
        return ""
    return f"{row[1]}{row[2]}"


def _pad_or_trim_row(row_values: list[str], target_width: int) -> list[str]:
    if len(row_values) < target_width:
        return row_values + [""] * (target_width - len(row_values))
    return row_values[:target_width]


def parse_aemo_csv_file(file_path: Path, table_name_pattern: str, logger) -> pd.DataFrame:
    """
    Parse AEMO C/I/D files safely using Python's csv module.

    The parser:
    - ignores C rows
    - ignores END OF REPORT rows
    - stores I rows as headers for each logical table
    - converts matching D rows into a rectangular DataFrame
    """
    logger.info("Parsing AEMO CSV file: %s", file_path.name)
    headers_by_table: dict[str, list[str]] = {}
    parsed_rows: list[list[str]] = []
    parsed_count_by_table: dict[str, int] = {}
    matched_table_name: str | None = None

    with file_path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if not row:
                continue

            joined_row = ",".join(row).upper()
            row_type = row[0].strip().upper()
            if row_type == "C" or "END OF REPORT" in joined_row:
                continue

            logical_name = logical_table_name_from_row(row)
            if row_type == "I" and table_name_matches(logical_name, table_name_pattern):
                matched_table_name = logical_name
                headers_by_table[logical_name] = [normalise_column_name(value) for value in row[4:]]
                logger.info("Found header row for logical table %s in %s", logical_name, file_path.name)
                continue

            if row_type == "D" and table_name_matches(logical_name, table_name_pattern):
                header_values = headers_by_table.get(logical_name)
                if not header_values:
                    logger.warning(
                        "Skipping a %s data row in %s because no header row was found first",
                        logical_name,
                        file_path.name,
                    )
                    continue

                parsed_rows.append(_pad_or_trim_row(row[4:], len(header_values)))
                parsed_count_by_table[logical_name] = parsed_count_by_table.get(logical_name, 0) + 1

    for logical_name, row_count in parsed_count_by_table.items():
        logger.info("Parsed %s rows for logical table %s from %s", row_count, logical_name, file_path.name)

    if not parsed_rows or matched_table_name is None:
        logger.warning("No matching %s rows were parsed from %s", table_name_pattern, file_path.name)
        return pd.DataFrame()

    dataframe = pd.DataFrame(parsed_rows, columns=headers_by_table[matched_table_name])
    dataframe["raw_source_file"] = file_path.name
    dataframe["raw_table_name"] = matched_table_name
    return dataframe


def parse_tabular_file(file_path: Path, table_name_pattern: str, logger) -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return parse_aemo_csv_file(file_path, table_name_pattern, logger)

    logger.info("Parsing Excel file: %s", file_path.name)
    try:
        if suffix == ".xlsx":
            dataframe = pd.read_excel(file_path, engine="openpyxl")
        else:
            dataframe = pd.read_excel(file_path)
    except Exception as exc:
        logger.error("Failed to parse Excel file %s: %s", file_path.name, exc)
        return pd.DataFrame()

    dataframe.columns = [normalise_column_name(column) for column in dataframe.columns]
    dataframe["raw_source_file"] = file_path.name
    dataframe["raw_table_name"] = table_name_pattern
    logger.info("Parsed %s rows from Excel file %s", len(dataframe), file_path.name)
    return dataframe
