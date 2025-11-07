#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./cleanup_and_verify.sh --delete-verified-users
#   ./cleanup_and_verify.sh --verify-from-json exports/proz_us_seed.json

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

python -m app.scripts.cleanup_and_verify "$@"

echo "Done."


