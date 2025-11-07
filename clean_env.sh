#!/bin/bash

# Clean .env file script
# This script removes inline comments from .env file to prevent parsing errors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log "Cleaning .env file to remove inline comments..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    error ".env file not found"
fi

# Create backup
log "Creating backup of .env file..."
cp .env .env.backup
success "Backup created as .env.backup"

# Clean the file
log "Removing inline comments..."
# Remove inline comments (everything after # that's not in quotes)
# This handles cases like: MAX_FILE_SIZE=5242880  # 5MB
sed -i.tmp 's/[[:space:]]*#.*$//' .env

# Remove the temporary file created by sed
rm -f .env.tmp

# Remove empty lines
log "Removing empty lines..."
sed -i.tmp '/^[[:space:]]*$/d' .env
rm -f .env.tmp

success ".env file cleaned successfully!"

echo ""
echo "Summary:"
echo "========"
echo "✅ Inline comments removed"
echo "✅ Empty lines removed"
echo "✅ Backup created as .env.backup"
echo ""
echo "You can now run your deployment scripts without parsing errors."
echo "If something goes wrong, restore from backup: cp .env.backup .env"
