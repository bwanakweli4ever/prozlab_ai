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

# 4. Check .env exists (loaded by Python via pydantic-settings)
if [ ! -f ".env" ]; then
    error ".env file not found"
fi

# 5–7. Test DB connection and create superuser (Python reads .env correctly, including # in passwords)
log "Testing database connection..."
python -c "
import sys
sys.path.append('.')

from sqlalchemy import text
from app.config.settings import settings
from app.config.database import engine
from app.database.session import get_db
from app.modules.auth.models.user import User
from app.core.security import get_password_hash

required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
missing = [k for k in required if not getattr(settings, k, None)]
if missing:
    print(f'❌ Missing required environment variables: {\", \".join(missing)}')
    sys.exit(1)

try:
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ Database connection successful!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    print('   Check DB_* values in .env and that PostgreSQL is running (pg_isready -h localhost).')
    sys.exit(1)

email = 'mucyoelie84@gmail.com'
password = 'kigali123'
first_name = 'Admin'
last_name = 'User'

db = next(get_db())
try:
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        existing_user.is_superuser = True
        existing_user.is_active = True
        existing_user.hashed_password = get_password_hash(password)
        db.commit()
        print(f'✅ Superuser ready (password reset): {email}')
        print(f'   User ID: {existing_user.id}')
        sys.exit(0)

    new_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        is_superuser=True,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print('✅ Superuser created successfully!')
    print(f'   Email: {email}')
    print(f'   Name: {first_name} {last_name}')
    print(f'   User ID: {new_user.id}')
except Exception as e:
    print(f'❌ Error creating superuser: {e}')
    sys.exit(1)
finally:
    db.close()
" || error "Superuser setup failed — see error above."

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

