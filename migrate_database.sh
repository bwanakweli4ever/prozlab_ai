#!/bin/bash

# Database Migration Script for ProzLab Backend
# This script only handles database migrations without starting the application

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

log "Starting database migration for ProzLab Backend..."

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

# 4. Install/upgrade dependencies
log "Installing/upgrading dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Check if .env file exists
if [ ! -f ".env" ]; then
    warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warning "Please edit .env file with your production values before continuing"
        warning "Required: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
        read -p "Press Enter after updating .env file..."
    else
        error ".env.example not found. Please create .env file manually with required environment variables"
    fi
fi

# 6. Load environment variables
log "Loading environment variables..."
# Load .env file safely, ignoring comments and empty lines
if [ -f ".env" ]; then
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
    error ".env file not found"
fi

# 7. Check database connection
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

# 8. Show current migration status
log "Current migration status:"
alembic current

# 9. Show available migrations
log "Available migrations:"
alembic history --verbose

# 10. Check for migration conflicts
log "Checking for migration conflicts..."
HEADS_COUNT=$(alembic heads | wc -l)
if [ "$HEADS_COUNT" -gt 1 ]; then
    warning "Multiple migration heads detected:"
    alembic heads
    echo ""
    warning "This might indicate a merge conflict. You may need to merge migrations."
    read -p "Do you want to continue with migration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Migration cancelled by user"
    fi
fi

# 11. Run database migrations
log "Running database migrations..."
alembic upgrade head

# 12. Verify migration was successful
log "Verifying migration status..."
alembic current

# 13. Show final migration status
log "Final migration status:"
alembic history --verbose

success "Database migration completed successfully!"

echo ""
echo "Migration Summary:"
echo "=================="
echo "✅ Database connection verified"
echo "✅ Migrations applied successfully"
echo "✅ Database schema is up to date"
echo ""
echo "You can now start your application with:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
