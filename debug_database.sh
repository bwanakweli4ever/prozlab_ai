#!/bin/bash

# Database Debug Script for ProzLab Backend
# This script helps debug database connection issues

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

log "Starting database debug for ProzLab Backend..."

# 1. Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    error "Please run this script from the project root directory (where app/main.py exists)"
fi

# 2. Check if .env file exists
if [ ! -f ".env" ]; then
    error ".env file not found. Please create it first."
fi

# 3. Show .env file contents (masking passwords)
log "Checking .env file contents..."
echo "========================"
while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*# ]]; then
        echo "$line"  # Show comments as-is
    elif [[ -n "$line" ]]; then
        # Mask password values
        if [[ "$line" =~ ^[A-Z_]*PASSWORD= ]]; then
            key=$(echo "$line" | cut -d'=' -f1)
            echo "${key}=***MASKED***"
        else
            echo "$line"
        fi
    fi
done < .env
echo "========================"

# 4. Load environment variables
log "Loading environment variables..."
# Load .env file safely, ignoring comments and empty lines
if [ -f ".env" ]; then
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            # Remove inline comments (everything after # that's not in quotes)
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

# 5. Check if required environment variables are set
log "Checking required environment variables..."
required_vars=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER" "DB_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        if [ "$var" = "DB_PASSWORD" ]; then
            echo "✅ $var is set (***MASKED***)"
        else
            echo "✅ $var is set to: ${!var}"
        fi
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    error "Missing required environment variables: ${missing_vars[*]}"
fi

# 6. Test PostgreSQL connection directly
log "Testing PostgreSQL connection directly..."
if command -v psql &> /dev/null; then
    echo "Testing with psql command..."
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
        success "Direct PostgreSQL connection successful!"
    else
        error "Direct PostgreSQL connection failed. Check your credentials."
    fi
else
    warning "psql command not found. Skipping direct connection test."
fi

# 7. Test with Python
log "Testing with Python SQLAlchemy..."
python -c "
import sys
sys.path.append('.')
from app.config.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Python SQLAlchemy connection successful!')
        print(f'Database URL: {engine.url}')
except Exception as e:
    print(f'❌ Python SQLAlchemy connection failed: {e}')
    print('This is the error you need to fix.')
    sys.exit(1)
"

# 8. Check if database exists
log "Checking if database exists..."
if command -v psql &> /dev/null; then
    echo "Checking if database '$DB_NAME' exists..."
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        success "Database '$DB_NAME' exists"
    else
        warning "Database '$DB_NAME' does not exist. You may need to create it."
        echo "To create the database, run:"
        echo "sudo -u postgres psql"
        echo "CREATE DATABASE $DB_NAME;"
        echo "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        echo "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    fi
fi

# 9. Check if user exists
log "Checking if user exists..."
if command -v psql &> /dev/null; then
    echo "Checking if user '$DB_USER' exists..."
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1;" &> /dev/null; then
        success "User '$DB_USER' exists and can connect"
    else
        warning "User '$DB_USER' may not exist or password is incorrect."
        echo "To create the user, run:"
        echo "sudo -u postgres psql"
        echo "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        echo "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    fi
fi

success "Database debug completed!"

echo ""
echo "Summary:"
echo "========"
echo "If you see connection errors above, you need to:"
echo "1. Check your .env file has correct database credentials"
echo "2. Create the database user if it doesn't exist"
echo "3. Create the database if it doesn't exist"
echo "4. Grant proper permissions to the user"
