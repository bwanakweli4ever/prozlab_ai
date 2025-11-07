#!/bin/bash

# Database Rollback Script for ProzLab Backend
# This script allows you to rollback database migrations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log "Starting database rollback for ProzLab Backend..."

# 1. Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    error "Please run this script from the project root directory (where app/main.py exists)"
fi

# 2. Check if virtual environment exists
if [ ! -d "venv" ]; then
    error "Virtual environment not found. Please create it first with: python -m venv venv"
fi

# 3. Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# 4. Load environment variables
if [ -f ".env" ]; then
    log "Loading environment variables..."
    # Load .env file safely, ignoring comments and empty lines
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            # Remove inline comments (everything after # that's not in quotes)
            # This handles cases like: MAX_FILE_SIZE=5242880  # 5MB
            clean_line=$(echo "$line" | sed 's/[[:space:]]*#.*$//')
            # Only export if there's still content after removing comments
            if [[ -n "$clean_line" ]]; then
                export "$clean_line"
            fi
        fi
    done < .env
else
    warning ".env file not found. Make sure database credentials are set in environment"
fi

# 5. Check database connection
log "Testing database connection..."
python -c "
import sys
sys.path.append('.')
from app.config.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

# 6. Show current migration status
log "Current migration status:"
alembic current

# 7. Show migration history
log "Migration history:"
alembic history --verbose

# 8. Get rollback target
echo ""
echo "Available rollback options:"
echo "1. Rollback to previous migration (alembic downgrade -1)"
echo "2. Rollback to specific migration (alembic downgrade <revision_id>)"
echo "3. Rollback to base (alembic downgrade base) - WARNING: This will drop all tables!"
echo "4. Cancel rollback"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        log "Rolling back to previous migration..."
        alembic downgrade -1
        ;;
    2)
        echo ""
        log "Available migration revisions:"
        alembic history --verbose | grep -E "^[a-f0-9]{12}"
        echo ""
        read -p "Enter revision ID to rollback to: " revision_id
        if [ -z "$revision_id" ]; then
            error "No revision ID provided"
        fi
        log "Rolling back to revision: $revision_id"
        alembic downgrade "$revision_id"
        ;;
    3)
        warning "WARNING: This will drop ALL tables and data!"
        read -p "Are you sure you want to rollback to base? Type 'yes' to confirm: " confirm
        if [ "$confirm" = "yes" ]; then
            log "Rolling back to base (dropping all tables)..."
            alembic downgrade base
        else
            log "Rollback cancelled"
            exit 0
        fi
        ;;
    4)
        log "Rollback cancelled"
        exit 0
        ;;
    *)
        error "Invalid option selected"
        ;;
esac

# 9. Verify rollback was successful
log "Verifying rollback status..."
alembic current

# 10. Show final migration status
log "Final migration status:"
alembic history --verbose

success "Database rollback completed successfully!"

echo ""
echo "Rollback Summary:"
echo "================="
echo "✅ Database connection verified"
echo "✅ Rollback completed successfully"
echo "✅ Database schema updated"
echo ""
echo "Current migration status:"
alembic current
