from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "datasets.yaml"
LOG_PATH = PROJECT_ROOT / "logs" / "pipeline_log.txt"


BUSINESS_MODELS = {
    "price_drivers_analysis": {
        "label": "Price Drivers Analysis",
        "description": "Use regional dispatch and trading datasets to explain price movements and market outcomes.",
        "datasets": ["dispatch_price", "trading_regionsum", "dispatch_regionsum"],
    },
    "demand_net_demand_analysis": {
        "label": "Demand & Net Demand Analysis",
        "description": "Focus on operational demand, regional summaries, and rooftop PV to study net demand.",
        "datasets": ["dispatch_regionsum", "trading_regionsum", "rooftop_pv_actual"],
    },
    "bess_trading_analysis": {
        "label": "BESS Trading Analysis",
        "description": "Combine prices, SCADA, bids, and constraints to study battery dispatch and market behaviour.",
        "datasets": [
            "dispatch_price",
            "dispatch_regionsum",
            "trading_regionsum",
            "dispatch_unit_scada",
            "bids_per_offer",
            "bid_day_offer",
            "dispatch_constraints",
        ],
    },
    "fcas_market_analysis": {
        "label": "FCAS Market Analysis",
        "description": "Use FCAS-related price, requirement, recovery, and constraint datasets for ancillary service analysis.",
        "datasets": [
            "dispatch_price",
            "fcas_price",
            "fcas_requirements",
            "fcas_recovery",
            "fcas_constraints",
            "dispatch_unit_scada",
        ],
    },
    "network_constraints_analysis": {
        "label": "Network Constraints Analysis",
        "description": "Study regional prices, dispatch constraints, constraint metadata, and interconnector outcomes.",
        "datasets": [
            "dispatch_price",
            "dispatch_constraints",
            "constraint_rhs",
            "constraint_details",
            "constraint_equations",
            "interconnector_results",
        ],
    },
    "renewable_integration_analysis": {
        "label": "Renewable Integration Analysis",
        "description": "Use demand, rooftop PV, intermittent, semi-scheduled, and SCADA data to study renewable integration.",
        "datasets": [
            "dispatch_regionsum",
            "trading_regionsum",
            "rooftop_pv_actual",
            "intermittent_generation",
            "semi_scheduled_generation",
            "dispatch_unit_scada",
        ],
    },
    "full_nem_market_dataset": {
        "label": "Full NEM Market Dataset",
        "description": "Select every dataset that is currently enabled in the YAML configuration.",
        "datasets": "__ENABLED__",
    },
    "custom_dataset_selection": {
        "label": "Custom Dataset Selection",
        "description": "Choose only the tables you want to load for a custom workflow.",
        "datasets": [],
    },
}


class CallbackLogHandler(logging.Handler):
    """Small logging handler that mirrors formatted log lines into a callback."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.callback(self.format(record))
        except Exception:
            pass


def ensure_project_directories() -> None:
    for folder in ["logs", "data"]:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def setup_logger(log_file: Path | None = None, callback: Callable[[str], None] | None = None) -> logging.Logger:
    """Create a fresh logger for each pipeline run."""
    ensure_project_directories()
    logger = logging.getLogger("nemweb_pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file or LOG_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if callback is not None:
        callback_handler = CallbackLogHandler(callback)
        callback_handler.setFormatter(formatter)
        logger.addHandler(callback_handler)

    return logger


def load_dataset_config(config_path: Path | None = None) -> dict:
    """
    Load YAML config and normalise dataset definitions into a dict keyed by dataset name.

    The YAML file may store datasets as either a list or a dictionary.
    """
    path = config_path or CONFIG_PATH
    with path.open("r", encoding="utf-8") as file_handle:
        raw_config = yaml.safe_load(file_handle) or {}

    datasets = raw_config.get("datasets", {})
    if isinstance(datasets, list):
        normalised = {}
        for dataset in datasets:
            dataset_copy = dict(dataset)
            normalised[dataset_copy["name"]] = dataset_copy
        raw_config["datasets"] = normalised

    return raw_config


def get_enabled_dataset_names(config: dict) -> list[str]:
    return [
        dataset_name
        for dataset_name, dataset_config in config.get("datasets", {}).items()
        if dataset_config.get("enabled", False)
    ]


def resolve_business_model_datasets(model_name: str, config: dict, enabled_only: bool = False) -> list[str]:
    model = BUSINESS_MODELS.get(model_name)
    if not model:
        return []
    if model["datasets"] == "__ENABLED__":
        return get_enabled_dataset_names(config)
    resolved = [dataset_name for dataset_name in model["datasets"] if dataset_name in config.get("datasets", {})]
    if enabled_only:
        return [
            dataset_name
            for dataset_name in resolved
            if config["datasets"][dataset_name].get("enabled", False)
        ]
    return resolved


def parse_date_input(date_text: str, end_of_day: bool = False) -> datetime:
    cleaned = str(date_text).strip()
    supported_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in supported_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if fmt in ("%Y-%m-%d", "%Y/%m/%d") and end_of_day:
                return parsed + timedelta(days=1) - timedelta(seconds=1)
            return parsed
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format '{date_text}'. Use YYYY-MM-DD.")


def dates_from_year_month(year: int | str, month: int | str) -> tuple[str, str]:
    start_date = datetime(int(year), int(month), 1)
    if int(month) == 12:
        end_date = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(int(year), int(month) + 1, 1) - timedelta(days=1)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def normalise_column_name(column_name: str) -> str:
    column_name = str(column_name).strip().lower()
    column_name = re.sub(r"\s+", "_", column_name)
    column_name = re.sub(r"[^a-z0-9_]", "", column_name)
    column_name = re.sub(r"_+", "_", column_name).strip("_")
    return column_name


def normalise_table_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def table_name_matches(logical_name: str, pattern: str) -> bool:
    left = normalise_table_name(logical_name)
    right = normalise_table_name(pattern)
    return left == right or left in right or right in left


def safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def infer_filename_date_tokens(file_name: str) -> dict[str, list[datetime]]:
    """
    Extract daily and monthly date hints from NEMWeb filenames.

    Example:
    - PUBLIC_DISPATCHIS_202604240105_... -> daily token 2026-04-24
    - PUBLIC_foo_202604_...             -> monthly token 2026-04-01
    """
    text = file_name.upper()
    daily_matches: list[datetime] = []
    monthly_matches: list[datetime] = []

    for token in re.findall(r"(20\d{6})", text):
        try:
            daily_matches.append(datetime.strptime(token, "%Y%m%d"))
        except ValueError:
            continue

    for token in re.findall(r"(20\d{4})", text):
        try:
            monthly_matches.append(datetime.strptime(token + "01", "%Y%m%d"))
        except ValueError:
            continue

    return {"daily": daily_matches, "monthly": monthly_matches}


def filename_likely_in_range(file_name: str, start_dt: datetime, end_dt: datetime) -> bool:
    """
    Use filename hints as a pre-filter, but keep it permissive.

    Daily tokens must fall within the requested date range.
    Monthly tokens only need to overlap the requested month window.
    If no tokens are found, keep the file.
    """
    tokens = infer_filename_date_tokens(file_name)
    daily_matches = tokens["daily"]
    monthly_matches = tokens["monthly"]

    if daily_matches and any(start_dt.date() <= candidate.date() <= end_dt.date() for candidate in daily_matches):
        return True

    if monthly_matches:
        request_start_month = start_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        request_end_month = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if any(request_start_month <= candidate <= request_end_month for candidate in monthly_matches):
            return True

    return not daily_matches and not monthly_matches


def coerce_numeric_columns(dataframe: pd.DataFrame, exclude: Optional[Sequence[str]] = None) -> pd.DataFrame:
    exclude_set = set(exclude or [])
    for column in dataframe.columns:
        if column in exclude_set:
            continue
        if dataframe[column].dtype == object:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="ignore")
    return dataframe


def clear_log_file(log_path: Path | None = None) -> None:
    ensure_project_directories()
    target = log_path or LOG_PATH
    target.write_text("", encoding="utf-8")


def recent_log_tail(log_path: Path | None = None, max_lines: int = 200) -> str:
    target = log_path or LOG_PATH
    if not target.exists():
        return ""
    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-max_lines:])


def serialise_datetime(value: datetime | pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    return value.strftime("%Y-%m-%d %H:%M:%S")


def flatten(items: Iterable[Iterable[str]]) -> list[str]:
    flattened: list[str] = []
    for item in items:
        flattened.extend(item)
    return flattened
