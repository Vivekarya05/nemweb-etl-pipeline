from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from clean import clean_dataframe
from db import describe_existing_status, get_engine, get_existing_data_status
from extract import cleanup_temp_files, discover_dataset_links, prepare_dataset_files
from load import load_dataframe_to_database
from parser import parse_tabular_file
from utils import (
    BUSINESS_MODELS,
    CONFIG_PATH,
    clear_log_file,
    dates_from_year_month,
    load_dataset_config,
    parse_date_input,
    resolve_business_model_datasets,
    setup_logger,
)
from validate import validate_dataframe


PROGRESS_STAGES = [
    "Connecting to database",
    "Reading dataset config",
    "Checking duplicate data",
    "Scanning NEMWeb directories",
    "Downloading files",
    "Extracting ZIP and nested ZIP files",
    "Parsing AEMO C/I/D records",
    "Cleaning data",
    "Validating data",
    "Creating schemas and tables",
    "Loading into PostgreSQL",
    "Completed",
]


ProgressCallback = Callable[[str, str], None]


def emit_progress(callback: ProgressCallback | None, stage: str, message: str) -> None:
    if callback is not None:
        callback(stage, message)


def run_dataset_pipeline(
    dataset_name: str,
    dataset_config: dict,
    start_dt,
    end_dt,
    logger,
    engine,
    force_reload: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    logger.info("Dataset started: %s", dataset_name)
    summary = {
        "dataset": dataset_name,
        "display_name": dataset_config.get("display_name", dataset_name),
        "status": "skipped",
        "files_detected": 0,
        "rows_loaded": 0,
        "already_loaded": False,
        "tables_created": 0,
        "existing_rows_skipped": 0,
        "overlapping_rows_deleted": 0,
        "message": "",
        "error": "",
    }

    file_paths: list[Path] = []
    try:
        emit_progress(progress_callback, PROGRESS_STAGES[2], f"Checking duplicate data for {dataset_name}")
        existing_status = get_existing_data_status(
            engine=engine,
            schema_name=dataset_config["target_schema"],
            table_name=dataset_config["target_table"],
            datetime_column=dataset_config["datetime_column"].lower(),
            start_dt=start_dt,
            end_dt=end_dt,
        )
        described_existing_status = describe_existing_status(existing_status)
        logger.info("Duplicate check result for %s: %s", dataset_name, described_existing_status["status_message"])
        summary["already_loaded"] = described_existing_status["already_loaded"]
        summary["existing_rows_skipped"] = described_existing_status["rows_in_range"] if described_existing_status["already_loaded"] else 0

        if described_existing_status["already_loaded"] and not force_reload:
            summary["status"] = "already_exists"
            summary["message"] = described_existing_status["status_message"]
            return summary

        emit_progress(progress_callback, PROGRESS_STAGES[3], f"Scanning NEMWeb directories for {dataset_name}")
        file_links = discover_dataset_links(
            directory_urls=dataset_config["directory_urls"],
            file_name_pattern=dataset_config["file_name_pattern"],
            start_dt=start_dt,
            end_dt=end_dt,
            logger=logger,
        )
        summary["files_detected"] = len(file_links)
        logger.info("Files found for %s: %s", dataset_name, len(file_links))

        if not file_links:
            summary["message"] = "No matching files were found in the scanned NEMWeb directories."
            return summary

        emit_progress(progress_callback, PROGRESS_STAGES[4], f"Downloading files for {dataset_name}")
        emit_progress(progress_callback, PROGRESS_STAGES[5], f"Extracting files for {dataset_name}")
        file_paths = prepare_dataset_files(file_links, logger)

        emit_progress(progress_callback, PROGRESS_STAGES[6], f"Parsing AEMO records for {dataset_name}")
        parsed_frames: list[pd.DataFrame] = []
        for file_path in file_paths:
            parsed_frame = parse_tabular_file(file_path, dataset_config["table_name_pattern"], logger)
            if not parsed_frame.empty:
                parsed_frames.append(parsed_frame)

        if not parsed_frames:
            summary["message"] = "No rows were parsed from the detected files."
            return summary

        combined_df = pd.concat(parsed_frames, ignore_index=True)
        logger.info("Rows parsed for %s: %s", dataset_name, len(combined_df))

        emit_progress(progress_callback, PROGRESS_STAGES[7], f"Cleaning data for {dataset_name}")
        cleaned_df = clean_dataframe(combined_df, dataset_config, start_dt, end_dt, logger)
        if cleaned_df.empty:
            summary["message"] = "No rows remained after cleaning and date filtering."
            return summary

        emit_progress(progress_callback, PROGRESS_STAGES[8], f"Validating data for {dataset_name}")
        if not validate_dataframe(cleaned_df, dataset_config, logger):
            summary["status"] = "failed"
            summary["message"] = "Validation failed for the selected dataset."
            return summary

        emit_progress(progress_callback, PROGRESS_STAGES[9], f"Creating schemas and tables for {dataset_name}")
        emit_progress(progress_callback, PROGRESS_STAGES[10], f"Loading rows into PostgreSQL for {dataset_name}")
        load_result = load_dataframe_to_database(cleaned_df, dataset_config, engine, logger)

        summary["status"] = "success"
        summary["rows_loaded"] = load_result["rows_loaded"]
        summary["tables_created"] = 1 if load_result["table_created"] else 0
        summary["overlapping_rows_deleted"] = load_result["overlapping_rows_deleted"]
        summary["message"] = (
            f"Loaded {load_result['rows_loaded']} rows into "
            f"{dataset_config['target_schema']}.{dataset_config['target_table']}."
        )
        return summary
    except Exception as exc:
        logger.exception("Dataset %s failed with error: %s", dataset_name, exc)
        summary["status"] = "failed"
        summary["message"] = str(exc)
        summary["error"] = str(exc)
        return summary
    finally:
        cleanup_temp_files(file_paths, logger)


def run_pipeline(
    start: str | None = None,
    end: str | None = None,
    selected_datasets: Optional[list[str]] = None,
    config_path: Path | None = None,
    force_reload: bool = False,
    business_model: str | None = None,
    year: str | None = None,
    month: str | None = None,
    progress_callback: ProgressCallback | None = None,
    log_callback: Callable[[str], None] | None = None,
    reset_logs: bool = False,
) -> dict:
    if year and month and (not start or not end):
        start, end = dates_from_year_month(year, month)

    if not start or not end:
        raise ValueError("A start date and end date are required.")

    if reset_logs:
        clear_log_file()

    logger = setup_logger(callback=log_callback)
    start_dt = parse_date_input(start, end_of_day=False)
    end_dt = parse_date_input(end, end_of_day=True)

    emit_progress(progress_callback, PROGRESS_STAGES[0], "Connecting to database")
    engine = get_engine()

    emit_progress(progress_callback, PROGRESS_STAGES[1], "Reading dataset config")
    config = load_dataset_config(config_path or CONFIG_PATH)
    datasets = config["datasets"]

    if selected_datasets:
        datasets_to_run = [name for name in selected_datasets if name in datasets]
    elif business_model and business_model != "custom_dataset_selection":
        datasets_to_run = resolve_business_model_datasets(business_model, config, enabled_only=True)
    else:
        datasets_to_run = [name for name, dataset in datasets.items() if dataset.get("enabled", False)]

    if not datasets_to_run:
        raise ValueError("No datasets were selected for the pipeline run.")

    logger.info("Database connection started")
    logger.info("Selected business model: %s", business_model or "custom_dataset_selection")
    logger.info("Selected datasets: %s", ", ".join(datasets_to_run))
    logger.info("Selected date range: %s to %s", start_dt, end_dt)

    results: list[dict] = []
    for dataset_name in datasets_to_run:
        result = run_dataset_pipeline(
            dataset_name=dataset_name,
            dataset_config=datasets[dataset_name],
            start_dt=start_dt,
            end_dt=end_dt,
            logger=logger,
            engine=engine,
            force_reload=force_reload,
            progress_callback=progress_callback,
        )
        results.append(result)

    emit_progress(progress_callback, PROGRESS_STAGES[11], "Completed")

    summary = {
        "current_status": "Failed" if any(result["status"] == "failed" for result in results) else "Completed",
        "selected_date_range": {"start_date": start, "end_date": end},
        "business_model": business_model or "custom_dataset_selection",
        "tables_selected": datasets_to_run,
        "tables_created": sum(result.get("tables_created", 0) for result in results),
        "rows_loaded": sum(result.get("rows_loaded", 0) for result in results),
        "existing_rows_skipped": sum(result.get("existing_rows_skipped", 0) for result in results),
        "errors": [result["message"] for result in results if result["status"] == "failed"],
        "results": results,
    }
    logger.info("Completed status: %s", summary["current_status"])
    return summary


def check_existing_data(start: str, end: str, selected_datasets: list[str], business_model: str | None = None) -> dict:
    config = load_dataset_config(CONFIG_PATH)
    if selected_datasets:
        dataset_names = [name for name in selected_datasets if name in config["datasets"]]
    elif business_model and business_model != "custom_dataset_selection":
        dataset_names = resolve_business_model_datasets(business_model, config, enabled_only=True)
    else:
        dataset_names = [name for name, dataset in config["datasets"].items() if dataset.get("enabled", False)]

    start_dt = parse_date_input(start, end_of_day=False)
    end_dt = parse_date_input(end, end_of_day=True)
    engine = get_engine()
    results = []
    for dataset_name in dataset_names:
        dataset_config = config["datasets"][dataset_name]
        existing_status = get_existing_data_status(
            engine=engine,
            schema_name=dataset_config["target_schema"],
            table_name=dataset_config["target_table"],
            datetime_column=dataset_config["datetime_column"].lower(),
            start_dt=start_dt,
            end_dt=end_dt,
        )
        described = describe_existing_status(existing_status)
        described["dataset"] = dataset_name
        described["display_name"] = dataset_config.get("display_name", dataset_name)
        described["target_table"] = f"{dataset_config['target_schema']}.{dataset_config['target_table']}"
        results.append(described)
    return {"results": results}


def diagnose_dataset(dataset_name: str, start: str, end: str) -> dict:
    """
    Run a lightweight diagnostic for one dataset without loading to PostgreSQL.
    This helps answer whether the issue is file discovery, parsing, cleaning,
    or database loading.
    """
    config = load_dataset_config(CONFIG_PATH)
    if dataset_name not in config["datasets"]:
        raise ValueError(f"Dataset '{dataset_name}' was not found in config/datasets.yaml.")

    dataset_config = config["datasets"][dataset_name]
    start_dt = parse_date_input(start, end_of_day=False)
    end_dt = parse_date_input(end, end_of_day=True)
    logger = setup_logger()

    file_paths: list[Path] = []
    try:
        file_links = discover_dataset_links(
            directory_urls=dataset_config["directory_urls"],
            file_name_pattern=dataset_config["file_name_pattern"],
            start_dt=start_dt,
            end_dt=end_dt,
            logger=logger,
        )
        file_paths = prepare_dataset_files(file_links, logger) if file_links else []

        parsed_frames: list[pd.DataFrame] = []
        for file_path in file_paths:
            parsed_frame = parse_tabular_file(file_path, dataset_config["table_name_pattern"], logger)
            if not parsed_frame.empty:
                parsed_frames.append(parsed_frame)

        parsed_row_count = int(sum(len(frame) for frame in parsed_frames))
        cleaned_row_count = 0
        if parsed_frames:
            combined_df = pd.concat(parsed_frames, ignore_index=True)
            cleaned_df = clean_dataframe(combined_df, dataset_config, start_dt, end_dt, logger)
            cleaned_row_count = int(len(cleaned_df))

        return {
            "ok": True,
            "dataset": dataset_name,
            "display_name": dataset_config.get("display_name", dataset_name),
            "files_detected": len(file_links),
            "files_extracted": len(file_paths),
            "rows_parsed": parsed_row_count,
            "rows_after_cleaning": cleaned_row_count,
            "message": (
                f"Diagnostic complete for {dataset_name}. "
                f"files_detected={len(file_links)}, files_extracted={len(file_paths)}, "
                f"rows_parsed={parsed_row_count}, rows_after_cleaning={cleaned_row_count}"
            ),
        }
    finally:
        cleanup_temp_files(file_paths, logger)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AEMO NEMWeb ETL pipeline.")
    parser.add_argument("--start", required=False, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end", required=False, help="End date in YYYY-MM-DD format")
    parser.add_argument("--year", required=False, help="Optional year used with --month")
    parser.add_argument("--month", required=False, help="Optional month used with --year")
    parser.add_argument("--business-model", required=False, choices=list(BUSINESS_MODELS.keys()))
    parser.add_argument("--datasets", nargs="*", default=None, help="Optional dataset names from config/datasets.yaml")
    parser.add_argument("--force-reload", action="store_true")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    summary = run_pipeline(
        start=args.start,
        end=args.end,
        year=args.year,
        month=args.month,
        business_model=args.business_model,
        selected_datasets=args.datasets,
        force_reload=args.force_reload,
    )
    has_failure = summary["current_status"] == "Failed"
    for result in summary["results"]:
        print(
            f"{result['dataset']}: status={result['status']} | files_detected={result['files_detected']} | "
            f"rows_loaded={result['rows_loaded']} | message={result['message']}"
        )
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
