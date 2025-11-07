#!/bin/bash

# Create Superuser Script for ProzLab Backend
# This script creates a superuser with the specified email and password

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

log "Creating superuser for ProzLab Backend..."

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

# 7. Create superuser using Python
log "Creating superuser..."
python -c "
import sys
sys.path.append('.')
from app.database.session import get_db
from app.modules.auth.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.orm import Session

# Superuser details
email = 'mucyoelie84@gmail.com'
password = 'kigali123'
first_name = 'Admin'
last_name = 'User'
is_superuser = True
is_active = True

try:
    # Get database session
    db = next(get_db())
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f'❌ User with email {email} already exists')
        sys.exit(1)
    
    # Create new superuser
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        first_name=first_name,
        last_name=last_name,
        is_superuser=is_superuser,
        is_active=is_active
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f'✅ Superuser created successfully!')
    print(f'   Email: {email}')
    print(f'   Name: {first_name} {last_name}')
    print(f'   User ID: {new_user.id}')
    print(f'   Is Superuser: {is_superuser}')
    print(f'   Is Active: {is_active}')
    
except Exception as e:
    print(f'❌ Error creating superuser: {e}')
    sys.exit(1)
finally:
    db.close()
"

success "Superuser creation completed!"

echo ""
echo "Superuser Details:"
echo "=================="
echo "Email: mucyoelie84@gmail.com"
echo "Password: kigali123"
echo "Role: Superuser (Admin)"
echo "Status: Active"
echo ""
echo "You can now login with these credentials!"

