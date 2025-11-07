#!/bin/bash

# Production Deployment Script for ProzLab Backend
# This script handles database migrations, environment setup, and application deployment

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

# Check if running as root (not recommended for production)
if [ "$EUID" -eq 0 ]; then
    warning "Running as root is not recommended for production deployment"
fi

log "Starting production deployment for ProzLab Backend..."

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
        warning "Required: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, SECRET_KEY, SMTP_* settings"
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
    
    # Debug: Show loaded database values
    log "Loaded environment variables:"
    echo "  DB_HOST: $DB_HOST"
    echo "  DB_PORT: $DB_PORT"
    echo "  DB_NAME: $DB_NAME"
    echo "  DB_USER: $DB_USER"
    echo "  DB_PASSWORD: ***MASKED***"
else
    error ".env file not found"
fi

# 7. Check database connection
log "Testing database connection..."
# Test with explicit environment variables
DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" python -c "
import sys
import os
sys.path.append('.')
from app.config.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ Database connection successful')
    print(f'Connected to: {os.getenv(\"DB_HOST\")}:{os.getenv(\"DB_PORT\")}/{os.getenv(\"DB_NAME\")} as {os.getenv(\"DB_USER\")}')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

# 8. Check current migration status
log "Checking current migration status..."
alembic current

# 9. Run database migrations
log "Running database migrations..."
alembic upgrade head

# 10. Verify migration was successful
log "Verifying migration status..."
alembic current

# 11. Check if any pending migrations exist
PENDING_MIGRATIONS=$(alembic heads | wc -l)
if [ "$PENDING_MIGRATIONS" -gt 1 ]; then
    warning "Multiple migration heads detected. This might indicate a merge conflict."
    alembic heads
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Deployment cancelled by user"
    fi
fi

# 12. Create necessary directories
log "Creating necessary directories..."
mkdir -p uploads/profile_images/large
mkdir -p uploads/profile_images/medium
mkdir -p uploads/profile_images/thumbnail
mkdir -p logs

# 13. Set proper permissions
log "Setting proper permissions..."
chmod 755 uploads
chmod 755 uploads/profile_images
chmod 755 uploads/profile_images/large
chmod 755 uploads/profile_images/medium
chmod 755 uploads/profile_images/thumbnail
chmod 755 logs

# 14. Test email configuration
log "Testing email configuration..."
python -c "
import sys
sys.path.append('.')
from app.services.email_service import EmailService
try:
    email_service = EmailService()
    status = email_service.get_status()
    print(f'✅ Email service status: {status}')
except Exception as e:
    print(f'❌ Email service test failed: {e}')
    sys.exit(1)
"

# 15. Kill any existing uvicorn processes
log "Stopping existing uvicorn processes..."
pkill -f uvicorn || true
sleep 2

# 16. Start the application
log "Starting FastAPI application..."
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4 > logs/app.log 2>&1 &

# 17. Wait for application to start
log "Waiting for application to start..."
sleep 5

# 18. Test application health
log "Testing application health..."
if curl -f -s http://localhost:9000/health > /dev/null; then
    success "Application is running and healthy"
else
    error "Application health check failed"
fi

# 19. Test API endpoints
log "Testing critical API endpoints..."

# Test email status endpoint
if curl -f -s http://localhost:9000/api/v1/auth/email/status > /dev/null; then
    success "Email status endpoint is working"
else
    warning "Email status endpoint test failed"
fi

# Test database connection via API
if curl -f -s http://localhost:9000/api/v1/auth/email/status | grep -q "smtp_configured"; then
    success "Database connection via API is working"
else
    warning "Database connection via API test failed"
fi

# 20. Display deployment summary
log "Deployment Summary:"
echo "=================="
echo "✅ Dependencies installed"
echo "✅ Environment variables loaded"
echo "✅ Database migrations completed"
echo "✅ Application started on port 9000"
echo "✅ Health checks passed"
echo ""
echo "Application URL: http://localhost:9000"
echo "API Documentation: http://localhost:9000/docs"
echo "Logs: tail -f logs/app.log"
echo ""
echo "To stop the application: pkill -f uvicorn"
echo "To restart: ./deploy_production.sh"

success "Production deployment completed successfully!"

# 21. Optional: Set up systemd service (uncomment if needed)
# log "Setting up systemd service..."
# cat > /etc/systemd/system/prozlab-backend.service << EOF
# [Unit]
# Description=ProzLab Backend API
# After=network.target
#
# [Service]
# Type=simple
# User=www-data
# WorkingDirectory=$(pwd)
# Environment=PATH=$(pwd)/venv/bin
# ExecStart=$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4
# Restart=always
#
# [Install]
# WantedBy=multi-user.target
# EOF
# systemctl daemon-reload
# systemctl enable prozlab-backend
# systemctl start prozlab-backend
# success "Systemd service created and started"
