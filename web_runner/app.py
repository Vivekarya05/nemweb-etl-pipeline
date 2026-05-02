from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from db import run_test_table_insert, test_database_connection  # noqa: E402
from main_pipeline import PROGRESS_STAGES, check_existing_data, diagnose_dataset, run_pipeline  # noqa: E402
from utils import BUSINESS_MODELS, clear_log_file, load_dataset_config, recent_log_tail  # noqa: E402


app = Flask(__name__)
JOB_STORE: dict[str, dict] = {}
ACTIVE_JOB_ID: str | None = None
JOB_LOCK = threading.Lock()


def append_job_log(job_id: str, log_line: str) -> None:
    with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        job["logs"].append(log_line)
        if len(job["logs"]) > 500:
            job["logs"] = job["logs"][-500:]


def update_job_stage(job_id: str, stage: str, message: str) -> None:
    with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        job["stage"] = stage
        job["message"] = message
        job["stage_index"] = PROGRESS_STAGES.index(stage) + 1 if stage in PROGRESS_STAGES else 0


def pipeline_worker(job_id: str, payload: dict) -> None:
    with JOB_LOCK:
        JOB_STORE[job_id]["status"] = "Processing"
        JOB_STORE[job_id]["started_at"] = time.time()
        JOB_STORE[job_id]["message"] = "Pipeline is processing. Please keep this window open."

    try:
        summary = run_pipeline(
            start=payload.get("start_date"),
            end=payload.get("end_date"),
            selected_datasets=payload.get("datasets", []),
            force_reload=payload.get("force_reload", False),
            business_model=payload.get("business_model"),
            year=payload.get("year"),
            month=payload.get("month"),
            progress_callback=lambda stage, message: update_job_stage(job_id, stage, message),
            log_callback=lambda line: append_job_log(job_id, line),
            reset_logs=True,
        )
        with JOB_LOCK:
            JOB_STORE[job_id]["status"] = summary["current_status"]
            JOB_STORE[job_id]["finished_at"] = time.time()
            JOB_STORE[job_id]["summary"] = summary
            JOB_STORE[job_id]["results"] = summary["results"]
            JOB_STORE[job_id]["message"] = "Pipeline completed successfully." if summary["current_status"] == "Completed" else "Pipeline completed with one or more failures."
            JOB_STORE[job_id]["stage"] = PROGRESS_STAGES[-1]
            JOB_STORE[job_id]["stage_index"] = len(PROGRESS_STAGES)
    except Exception as exc:
        append_job_log(job_id, f"ERROR | web_runner | {exc}")
        with JOB_LOCK:
            JOB_STORE[job_id]["status"] = "Failed"
            JOB_STORE[job_id]["finished_at"] = time.time()
            JOB_STORE[job_id]["error"] = str(exc)
            JOB_STORE[job_id]["message"] = "Pipeline failed."


def current_job_snapshot() -> dict:
    with JOB_LOCK:
        if ACTIVE_JOB_ID is None or ACTIVE_JOB_ID not in JOB_STORE:
            return {
                "status": "Idle",
                "message": "No pipeline is running right now.",
                "stage": "",
                "stage_index": 0,
                "elapsed_seconds": 0,
                "summary": None,
                "results": [],
                "request": {},
                "error": "",
            }
        job = dict(JOB_STORE[ACTIVE_JOB_ID])

    start_reference = job.get("started_at") or job.get("created_at") or time.time()
    end_reference = job.get("finished_at") or time.time()
    elapsed_seconds = max(0, int(end_reference - start_reference))
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "message": job.get("message", ""),
        "stage": job.get("stage", ""),
        "stage_index": job.get("stage_index", 0),
        "elapsed_seconds": elapsed_seconds,
        "summary": job.get("summary"),
        "results": job.get("results", []),
        "request": job.get("request", {}),
        "error": job.get("error", ""),
    }


@app.route("/", methods=["GET"])
def index():
    config = load_dataset_config()
    return render_template(
        "index.html",
        datasets=config["datasets"],
        business_models=BUSINESS_MODELS,
        progress_stages=PROGRESS_STAGES,
    )


@app.route("/run-pipeline", methods=["POST"])
def run_pipeline_route():
    payload = request.get_json(silent=True) or {}
    if not payload.get("start_date") and not (payload.get("year") and payload.get("month")):
        return jsonify({"ok": False, "error": "Provide a start date and end date, or choose a year and month."}), 400
    if not payload.get("end_date") and not (payload.get("year") and payload.get("month")):
        return jsonify({"ok": False, "error": "Provide a start date and end date, or choose a year and month."}), 400
    if not payload.get("datasets"):
        return jsonify({"ok": False, "error": "Select at least one dataset before running the pipeline."}), 400

    job_id = uuid.uuid4().hex
    job_record = {
        "job_id": job_id,
        "status": "Queued",
        "message": "Pipeline queued.",
        "stage": "",
        "stage_index": 0,
        "created_at": time.time(),
        "started_at": None,
        "finished_at": None,
        "request": payload,
        "results": [],
        "summary": None,
        "logs": [],
        "error": "",
    }

    global ACTIVE_JOB_ID
    with JOB_LOCK:
        JOB_STORE[job_id] = job_record
        ACTIVE_JOB_ID = job_id

    worker = threading.Thread(target=pipeline_worker, args=(job_id, payload), daemon=True)
    worker.start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/logs", methods=["GET"])
@app.route("/logs", methods=["GET"])
def logs_route():
    if request.path == "/logs" and "text/html" in (request.headers.get("Accept", "")) and not request.args.get("format"):
        return redirect(url_for("index"))
    with JOB_LOCK:
        if ACTIVE_JOB_ID and ACTIVE_JOB_ID in JOB_STORE:
            active_logs = JOB_STORE[ACTIVE_JOB_ID].get("logs", [])
            return jsonify({"ok": True, "logs": active_logs[-200:]})
    return jsonify({"ok": True, "logs": recent_log_tail().splitlines()})


@app.route("/check-existing-data", methods=["POST"])
def check_existing_data_route():
    payload = request.get_json(silent=True) or {}
    try:
        result = check_existing_data(
            start=payload.get("start_date"),
            end=payload.get("end_date"),
            selected_datasets=payload.get("datasets", []),
            business_model=payload.get("business_model"),
        )
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/clear-logs", methods=["POST"])
def clear_logs_route():
    clear_log_file()
    with JOB_LOCK:
        if ACTIVE_JOB_ID and ACTIVE_JOB_ID in JOB_STORE:
            JOB_STORE[ACTIVE_JOB_ID]["logs"] = []
    return jsonify({"ok": True, "message": "Logs cleared."})


@app.route("/api/status", methods=["GET"])
@app.route("/status", methods=["GET"])
def status_route():
    if request.path == "/status" and "text/html" in (request.headers.get("Accept", "")) and not request.args.get("format"):
        return redirect(url_for("index"))
    return jsonify({"ok": True, **current_job_snapshot()})


@app.route("/test-db-connection", methods=["POST"])
def test_db_connection_route():
    result = test_database_connection()
    status_code = 200 if result["ok"] else 500
    return jsonify(result), status_code


@app.route("/test-table-write", methods=["POST"])
def test_table_write_route():
    try:
        result = run_test_table_insert()
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/diagnose-dataset", methods=["POST"])
def diagnose_dataset_route():
    payload = request.get_json(silent=True) or {}
    dataset_name = payload.get("dataset")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    if not dataset_name or not start_date or not end_date:
        return jsonify({"ok": False, "error": "dataset, start_date, and end_date are required."}), 400
    try:
        result = diagnose_dataset(dataset_name, start_date, end_date)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
