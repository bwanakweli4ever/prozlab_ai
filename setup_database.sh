#!/bin/bash

# Database Setup Script for ProzLab Backend
# This script helps set up the PostgreSQL database and user

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

log "Setting up PostgreSQL database for ProzLab Backend..."

# 1. Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    error "Please run this script from the project root directory (where app/main.py exists)"
fi

# 2. Check if .env file exists
if [ ! -f ".env" ]; then
    error ".env file not found. Please create it first."
fi

# 3. Load environment variables
log "Loading environment variables..."
if [ -f ".env" ]; then
    while IFS= read -r line; do
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            clean_line=$(echo "$line" | sed 's/[[:space:]]*#.*$//')
            if [[ -n "$clean_line" ]]; then
                export "$clean_line"
            fi
        fi
    done < .env
else
    error ".env file not found"
fi

# 4. Check if PostgreSQL is running
log "Checking if PostgreSQL is running..."
if ! systemctl is-active --quiet postgresql; then
    warning "PostgreSQL is not running. Starting it..."
    sudo systemctl start postgresql
    sleep 2
fi

# 5. Check if required environment variables are set
log "Checking required environment variables..."
required_vars=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER" "DB_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    error "Missing required environment variables: ${missing_vars[*]}"
fi

# 6. Create database user
log "Creating database user '$DB_USER'..."
sudo -u postgres psql -c "DO \$\$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'User $DB_USER created successfully';
    ELSE
        RAISE NOTICE 'User $DB_USER already exists';
    END IF;
END
\$\$;"

# 7. Create database
log "Creating database '$DB_NAME'..."
sudo -u postgres psql -c "DO \$\$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') THEN
        CREATE DATABASE $DB_NAME OWNER $DB_USER;
        RAISE NOTICE 'Database $DB_NAME created successfully';
    ELSE
        RAISE NOTICE 'Database $DB_NAME already exists';
    END IF;
END
\$\$;"

# 8. Grant privileges
log "Granting privileges to user '$DB_USER'..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"

# 9. Test connection
log "Testing database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    success "Database connection successful!"
else
    error "Database connection failed. Please check your configuration."
fi

# 10. Show connection details
log "Database setup completed successfully!"
echo ""
echo "Database Details:"
echo "================="
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: ***MASKED***"
echo ""
echo "You can now run your deployment scripts:"
echo "  ./deploy_production.sh"
echo "  ./migrate_database.sh"
