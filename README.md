# AEMO NEMWeb Market Data Pipeline

This project is a local Flask web application for downloading, cleaning, validating, and loading AEMO NEMWeb market data into PostgreSQL.

It is designed for users who want a professional local dashboard instead of command-line-only workflows. The app helps you select dates, business models, and datasets, then runs the ETL pipeline and writes the results into PostgreSQL for analysis in pgAdmin, Power BI, or Python.

## Why Flask Instead Of Static HTML

This app uses Flask because a static `index.html` file cannot:

- run Python ETL code
- connect to PostgreSQL
- poll live pipeline status
- stream log updates
- test the database connection
- check for duplicate data before loading

That is why you must run the Flask app and open `http://127.0.0.1:5000`. Opening the raw template file with `file://` will not show the real application behaviour.

## What The App Does

The dashboard lets you:

- choose a start date and end date
- choose a year and month
- choose a business model / analysis type
- auto-select matching datasets
- manually adjust the dataset checklist
- test the PostgreSQL connection
- check whether data already exists
- run the NEMWeb pipeline
- watch live logs and progress stages
- load cleaned data into PostgreSQL

## Project Structure

```text
nemweb-etl-pipeline/
├── app.py
├── config/
│   └── datasets.yaml
├── sql/
│   ├── 00_create_database.sql
│   ├── 01_create_schemas.sql
│   ├── 02_create_tables.sql
│   └── 03_verify_loaded_data.sql
├── src/
│   ├── main_pipeline.py
│   ├── extract.py
│   ├── parser.py
│   ├── clean.py
│   ├── validate.py
│   ├── load.py
│   ├── db.py
│   └── utils.py
├── web_runner/
│   ├── app.py
│   └── templates/
│       └── index.html
├── logs/
│   └── .gitkeep
├── data/
│   └── .gitkeep
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## PostgreSQL Setup In pgAdmin

Run [sql/00_create_database.sql](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/sql/00_create_database.sql) while connected to a different database such as `postgres`.

```sql
CREATE DATABASE nemweb;
```

Then connect to the `nemweb` database and run [sql/01_create_schemas.sql](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/sql/01_create_schemas.sql):

```sql
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;
```

If you want manual backup tables before running Python, execute [sql/02_create_tables.sql](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/sql/02_create_tables.sql).

## Environment File

Create `.env` from `.env.example`:

```env
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nemweb
DB_USER=postgres
DB_PASSWORD=your_password
```

## Install Requirements

```bash
cd /Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run The Web App

Run the local website with:

```bash
python app.py
```

Then open:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

## How To Use The Dashboard

1. Test the database connection.
2. Select start date and end date, or choose year and month.
3. Choose a business model such as Price Drivers Analysis or BESS Trading Analysis.
4. Review the dataset checklist.
5. Click `Check Existing Data` if you want to inspect duplicates first.
6. Click `Run Pipeline`.
7. Watch progress stages and live logs.
8. Review result cards after completion.

## Business Models

The app includes these presets:

- Price Drivers Analysis
- Demand & Net Demand Analysis
- BESS Trading Analysis
- FCAS Market Analysis
- Network Constraints Analysis
- Renewable Integration Analysis
- Full NEM Market Dataset
- Custom Dataset Selection

Each preset automatically ticks the matching datasets in the checklist.

## Duplicate Prevention

Before loading, the pipeline checks the target table for rows in the selected date range.

- If the full selected period already exists, the app skips the load and reports:
  `Data already exists for this selected period. No duplicate load performed.`
- If partial overlap exists, overlapping rows are deleted and the selected period is reloaded cleanly.
- After loading, the app attempts to create a unique index on the configured primary key columns.

## Logs

Logs are written to:

- `logs/pipeline_log.txt`

The dashboard also polls the backend and shows recent log lines in a terminal-style panel.

Logged items include:

- database connection
- selected business model
- selected datasets
- selected date range
- NEMWeb URLs scanned
- files found
- files downloaded
- rows parsed
- rows cleaned
- validation warnings
- duplicate check results
- rows loaded
- completed status
- errors with traceback

## AEMO C/I/D Parser

AEMO files often contain mixed row types:

- `C` rows: control and report metadata
- `I` rows: logical table header rows
- `D` rows: actual data rows

Example:

```text
C,SETP.WORLD,DVD_DISPATCHPRICE,AEMO,PUBLIC,...
I,DISPATCH,PRICE,5,SETTLEMENTDATE,REGIONID,RRP,...
D,DISPATCH,PRICE,5,"2026/03/16 00:05:00",VIC1,45.2,...
```

This project does not use naive `pandas.read_csv()` for those payload files. Instead, [src/parser.py](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/src/parser.py):

- uses Python `csv`
- reads line by line
- detects `I` rows as headers
- detects `D` rows as records
- matches the requested logical table from `datasets.yaml`
- pads and trims variable-width rows safely
- ignores `C` rows and `END OF REPORT`

## How The Web App Works

Main Flask routes:

- `GET /`
- `POST /run-pipeline`
- `GET /logs`
- `POST /check-existing-data`
- `POST /clear-logs`
- `GET /status`
- `POST /test-db-connection`

The frontend JavaScript:

- auto-selects datasets when business model changes
- disables the run button during processing
- shows a spinner and runtime timer
- polls the backend every 1.5 seconds
- renders live logs
- renders progress stages
- renders completion and error cards

## Power BI Connection

To connect Power BI to PostgreSQL:

1. Open Power BI Desktop.
2. Choose `Get Data`.
3. Select `PostgreSQL database`.
4. Enter:
   - Server: `localhost`
   - Database: `nemweb`
5. Authenticate with your PostgreSQL username and password.
6. Select tables from the `raw` schema.

## Verify Data In pgAdmin

Run [sql/03_verify_loaded_data.sql](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/sql/03_verify_loaded_data.sql) after a pipeline run.

Example:

```sql
SELECT COUNT(*) FROM raw.dispatch_price;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_price;
SELECT * FROM raw.dispatch_price ORDER BY settlementdate DESC LIMIT 10;
```

## Add More AEMO Tables Later

1. Open [config/datasets.yaml](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/config/datasets.yaml).
2. Add a new dataset block.
3. Set:
   - `name`
   - `display_name`
   - `description`
   - `enabled`
   - `directory_urls`
   - `file_name_pattern`
   - `table_name_pattern`
   - `datetime_column`
   - `primary_keys`
   - `target_schema`
   - `target_table`
4. Add it to any business model preset in [src/utils.py](/Users/vivekarya/Documents/Codex/2026-04-26-act-as-a-senior-python-data/nemweb-etl-pipeline/src/utils.py) if needed.

## Run Commands

```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```
