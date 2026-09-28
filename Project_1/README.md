# MyProject_1
The first project about transfroming datas from sources used for DE path
# Python for DE — Mini ETL Pipeline

A small end-to-end ETL (Extract, Transform, Load) pipeline built in Python to
practice core Data Engineering skills: streaming file I/O, generators,
logging, error handling with retry, CLI arguments, and testing.

## Features

- Reads log and CSV data using streaming (no full file load into memory)
- Filters and aggregates data using generator pipelines
- Configurable via command-line arguments (`--date`, `--env`)
- Structured logging instead of `print()`
- Retry logic for simulated unstable operations
- Unit tests with `pytest`

## Project Structure

```
Project/
├── main.py              # Entry point: parses args, runs the pipeline
├── requirements.txt      # Python dependencies
├── access_sample.log     # Sample log data (input)
├── sales_sample.csv      # Sample sales data (input)
├── test_main.py           # Unit tests
└── .gitignore
```

## Requirements

- Python 3.10+
- pip

## Setup

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py --date 2026-09-16 --env dev
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `--date` | Yes | — | Processing date, format `YYYY-MM-DD` |
| `--env` | No | `dev` | Environment: `dev` or `prod` |

## Running Tests

```bash
pytest
```

## License

This project is for personal learning purposes.
