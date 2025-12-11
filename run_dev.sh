#!/usr/bin/env bash
set -e

source venv/bin/activate

export APP_ENV=dev

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
chmod +x run_dev.sh
