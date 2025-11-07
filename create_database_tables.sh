#!/bin/bash

# Complete Database Table Creation Script for ProzLab Backend
# This script creates a fresh database with all tables

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

log "Starting complete database table creation for ProzLab Backend..."

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

log "Database configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: ***MASKED***"

# 6. Test database connection
log "Testing database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    success "Database connection successful!"
else
    error "Database connection failed. Please check your credentials."
fi

# 7. Drop all existing tables (if any)
log "Dropping existing tables..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL ON SCHEMA public TO public;
"

# 8. Create all tables using SQLAlchemy
log "Creating all database tables..."
python -c "
import sys
sys.path.append('.')
from app.database.base_class import Base
from app.config.database import engine

# Import all models to ensure they are registered
from app.modules.auth.models.user import User
from app.modules.auth.models.otp import OTPVerification
from app.modules.auth.models.password_reset import PasswordResetToken
from app.modules.proz.models.proz import ProzProfile, ProzSpecialty, Specialty, Review
from app.modules.tasks.models.task import ServiceRequest, TaskAssignment, TaskNotification

# Create all tables
Base.metadata.create_all(bind=engine)
print('✅ All tables created successfully!')
"

# 9. Verify tables were created
log "Verifying tables were created..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

# 10. Create indexes for better performance
log "Creating database indexes..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
-- User indexes
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);

-- OTP indexes
CREATE INDEX IF NOT EXISTS ix_otp_verifications_id ON otp_verifications(id);
CREATE INDEX IF NOT EXISTS ix_otp_verifications_phone_number ON otp_verifications(phone_number);

-- Password reset indexes
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_id ON password_reset_tokens(id);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens(user_id);

-- Proz profile indexes
CREATE INDEX IF NOT EXISTS ix_proz_profiles_id ON proz_profiles(id);
CREATE INDEX IF NOT EXISTS ix_proz_profiles_email ON proz_profiles(email);

-- Specialty indexes
CREATE INDEX IF NOT EXISTS ix_specialties_id ON specialties(id);

-- Proz specialty indexes
CREATE INDEX IF NOT EXISTS ix_proz_specialty_id ON proz_specialty(id);

-- Review indexes
CREATE INDEX IF NOT EXISTS ix_reviews_id ON reviews(id);

-- Service request indexes
CREATE INDEX IF NOT EXISTS idx_service_requests_status ON service_requests(status);

-- Task assignment indexes
CREATE INDEX IF NOT EXISTS idx_task_assignments_proz_id ON task_assignments(proz_id);

-- Task notification indexes
CREATE INDEX IF NOT EXISTS idx_task_notifications_proz_id ON task_notifications(proz_id);
"

# 11. Insert some initial data (optional)
log "Inserting initial data..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
-- Insert some basic specialties
INSERT INTO specialties (id, name, description) VALUES 
('1', 'Web Development', 'Frontend and backend web development'),
('2', 'Mobile Development', 'iOS and Android app development'),
('3', 'Data Science', 'Data analysis and machine learning'),
('4', 'DevOps', 'Infrastructure and deployment automation'),
('5', 'UI/UX Design', 'User interface and experience design')
ON CONFLICT (id) DO NOTHING;
"

# 12. Set up Alembic to track the current state
log "Setting up Alembic migration tracking..."
# Create a new initial migration that represents the current state
alembic revision --autogenerate -m "initial_tables_created"

# Mark this as the current head
alembic stamp head

# 13. Final verification
log "Final verification..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
"

success "Database table creation completed successfully!"

echo ""
echo "Summary:"
echo "========"
echo "✅ Database connection verified"
echo "✅ All existing tables dropped"
echo "✅ All new tables created"
echo "✅ Database indexes created"
echo "✅ Initial data inserted"
echo "✅ Alembic migration tracking set up"
echo ""
echo "Your database is now ready for use!"
echo "You can now run: ./deploy_production.sh"

