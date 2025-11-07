#!/usr/bin/env bash
set -euo pipefail

# Usage: ./seed_proz_us.sh [--count 100] [--states "Texas,Pennsylvania"] [--out exports/proz_us_seed.json] [--dry]

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env || true
  set +a
fi

if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python -m pip install -q -r requirements.txt

python -m app.scripts.seed_proz_us "$@"

echo "Done."


