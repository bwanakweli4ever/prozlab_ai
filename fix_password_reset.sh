#!/bin/bash

# Fix and apply migrations for password reset functionality in production
# - Activates venv
# - Loads .env
# - Detects and merges multiple Alembic heads
# - Upgrades to latest migration
# - Verifies required tables/columns for password reset

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log "Starting password reset migration fix..."

# Ensure we're at project root
if [ ! -f "app/main.py" ]; then
    error "Run this script from the project root (where app/main.py exists)."
fi

# Activate venv
if [ -d "venv" ]; then
    log "Activating virtual environment..."
    # shellcheck source=/dev/null
    source venv/bin/activate
else
    error "Virtual environment 'venv' not found. Create it and install deps first."
fi

# Load .env if present
if [ -f ".env" ]; then
    log "Loading environment variables from .env..."
    # Export non-comment, non-empty lines, trimming inline comments
    while IFS= read -r line; do
        # skip empty and full-line comments
        if [[ -z "${line//[[:space:]]/}" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        # strip inline comments
        clean_line=$(echo "$line" | sed 's/[[:space:]]*#.*$//')
        if [[ -n "$clean_line" ]]; then
            export "$clean_line" || true
        fi
    done < .env
else
    warn ".env not found; relying on existing environment variables."
fi

# Verify required DB env vars if psql is available
if command -v psql >/dev/null 2>&1; then
    missing_vars=()
    for v in DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD; do
        if [ -z "${!v-}" ]; then
            missing_vars+=("$v")
        fi
    done
    if [ ${#missing_vars[@]} -gt 0 ]; then
        warn "Missing DB env vars (${missing_vars[*]}). Skipping direct psql connectivity test. Alembic may still work if it uses URL config."
    else
        log "Testing database connectivity with psql..."
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT}" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
            success "Database connection successful."
        else
            warn "Database connection test failed via psql. Proceeding with Alembic which may use app config."
        fi
    fi
else
    warn "psql not found; skipping direct DB connectivity test."
fi

# Ensure alembic executable
if [ ! -x "venv/bin/alembic" ]; then
    error "Alembic executable not found at venv/bin/alembic. Install dependencies in venv."
fi

log "Checking Alembic heads..."
HEADS_OUTPUT=$(venv/bin/alembic heads || true)
echo "$HEADS_OUTPUT"

# Extract 12-char revision ids from heads output
mapfile -t HEAD_IDS < <(echo "$HEADS_OUTPUT" | grep -oE '[0-9a-f]{12}' | sort -u)
NUM_HEADS=${#HEAD_IDS[@]}

if [ "$NUM_HEADS" -gt 1 ]; then
    log "Detected $NUM_HEADS heads: ${HEAD_IDS[*]}"
    log "Merging heads into a single revision..."
    venv/bin/alembic merge -m "Merge multiple heads for password reset rollout" "${HEAD_IDS[@]}"
    success "Heads merged."
else
    log "Single head detected. No merge necessary."
fi

log "Upgrading database to head..."
venv/bin/alembic upgrade head
success "Database upgraded to latest migration."

log "Verifying password reset schema..."
python - <<'PY'
from app.database.session import get_db
from sqlalchemy import text

db = next(get_db())
try:
    ok = True
    def check(msg, cond):
        global ok
        if cond:
            print(f"\033[0;32m[SUCCESS]\033[0m {msg}")
        else:
            print(f"\033[0;31m[ERROR]\033[0m {msg}")
            ok = False

    # password_reset_tokens table
    res = db.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name='password_reset_tokens'"))
    check("'password_reset_tokens' table exists", res.fetchone() is not None)

    # otp_verifications has email, purpose columns
    res = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'otp_verifications'
          AND column_name IN ('email','purpose')
    """))
    cols = {r[0] for r in res.fetchall()}
    check("'otp_verifications' has 'email' column", 'email' in cols)
    check("'otp_verifications' has 'purpose' column", 'purpose' in cols)

finally:
    db.close()
PY

success "Password reset migration fix completed."




