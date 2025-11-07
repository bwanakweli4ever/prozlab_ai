#!/bin/bash

set -euo pipefail

# Simple Alembic migration runner for ProzLab backend

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -f "alembic.ini" ]; then
  echo "Error: alembic.ini not found. Run this from the project root." >&2
  exit 1
fi

if [ -d "venv" ]; then
  # shellcheck source=/dev/null
  source "venv/bin/activate"
else
  echo "Warning: virtual environment 'venv' not found; using system Python." >&2
fi

if [ -f ".env" ]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    clean_line="$(echo "$line" | sed 's/[[:space:]]*#.*$//')"
    [[ -z "$clean_line" ]] && continue
    export "$clean_line"
  done < .env
fi

alembic upgrade head

