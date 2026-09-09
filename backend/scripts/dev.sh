#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CONDA_DEFAULT_ENV:-}" || "${CONDA_DEFAULT_ENV}" != "frame" ]]; then
  echo "[ERROR] Please activate conda env 'frame' first: conda activate frame"
  exit 1
fi

python -m pip install -r requirements.txt
if [[ -f ".env" ]]; then
  uvicorn app.main:app --reload --timeout-keep-alive 300 --env-file .env
else
  uvicorn app.main:app --reload --timeout-keep-alive 300
fi

