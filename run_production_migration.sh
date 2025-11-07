#!/bin/bash

# Production Migration Script for OTP Password Reset
# This script runs the latest migration on the production server

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

log "Starting production migration for OTP password reset system..."

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

# 5. Check required environment variables
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

# 6. Test database connection
log "Testing database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    success "Database connection successful!"
else
    error "Database connection failed. Please check your credentials."
fi

# 7. Check current migration status
log "Checking current migration status..."
current_revision=$(venv/bin/alembic current | grep -o '[a-f0-9]\{12\}' | head -1)
log "Current migration: $current_revision"

# 8. Check if migration is needed
if [ "$current_revision" = "3652d98b88df" ]; then
    success "Database is already up to date! No migration needed."
    exit 0
fi

# 9. Run the migration
log "Running migration to add email and purpose fields to OTP verifications..."
venv/bin/alembic upgrade head

# 10. Verify migration
log "Verifying migration..."
new_revision=$(venv/bin/alembic current | grep -o '[a-f0-9]\{12\}' | head -1)
if [ "$new_revision" = "3652d98b88df" ]; then
    success "Migration completed successfully!"
    success "Database is now ready for OTP-based password reset system"
else
    error "Migration verification failed. Current revision: $new_revision"
fi

# 11. Test the new functionality
log "Testing OTP functionality..."
python -c "
import sys
sys.path.append('.')
from app.database.session import get_db
from app.modules.auth.repositories.password_reset_otp_repository import PasswordResetOTPRepository

try:
    db = next(get_db())
    repo = PasswordResetOTPRepository()
    
    # Test OTP creation
    otp_obj = repo.create(db, 'test@example.com', expires_in_minutes=10)
    if otp_obj:
        print('✅ OTP creation test passed')
        print(f'   OTP Code: {otp_obj.otp_code}')
        print(f'   Email: {otp_obj.email}')
        print(f'   Purpose: {otp_obj.purpose}')
        
        # Clean up test OTP
        repo.delete_otps_for_email(db, 'test@example.com')
        print('✅ Test cleanup completed')
    else:
        print('❌ OTP creation test failed')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ OTP functionality test failed: {str(e)}')
    sys.exit(1)
finally:
    db.close()
"

success "Production migration completed successfully!"
success "OTP-based password reset system is now ready for use!"

echo ""
echo "Migration Summary:"
echo "=================="
echo "✅ Added 'email' field to otp_verifications table"
echo "✅ Added 'purpose' field to otp_verifications table" 
echo "✅ Added 'created_at' field to otp_verifications table"
echo "✅ Made 'phone_number' field nullable"
echo "✅ Added index on 'email' field"
echo "✅ OTP functionality tested and working"
echo ""
echo "New API Endpoints Available:"
echo "- POST /api/v1/auth/password/forgot (sends OTP)"
echo "- POST /api/v1/auth/password/verify-otp (verifies OTP)"
echo "- POST /api/v1/auth/password/reset-with-otp (resets password with OTP)"
