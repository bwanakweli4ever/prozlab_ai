# Production Deployment Guide

This guide covers deploying the ProzLab Backend to production using the provided deployment scripts.

## Prerequisites

- Ubuntu/Debian server (or similar Linux distribution)
- Python 3.12+
- PostgreSQL 12+
- Git
- Nginx (optional, for reverse proxy)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd prozlab_backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your production values
nano .env
```

**Required Environment Variables:**
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=prozlab_db
DB_USER=proz_user
DB_PASSWORD=your_secure_password

# JWT
SECRET_KEY=your_very_long_random_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# Email (Mailgun)
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@smtp.yourdomain.com
SMTP_PASSWORD=your_mailgun_smtp_password
EMAIL_FROM=noreply@yourdomain.com
MAIL_SUPPORT=support@yourdomain.com

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### 3. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE prozlab_db;
CREATE USER proz_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE prozlab_db TO proz_user;
\q
```

### 4. Deploy

**Option A: Full Deployment (Recommended)**
```bash
./deploy_production.sh
```

**Option B: Database Only**
```bash
./migrate_database.sh
```

## Deployment Scripts

### `deploy_production.sh`
Complete production deployment including:
- ✅ Dependency installation
- ✅ Environment setup
- ✅ Database migrations
- ✅ Application startup
- ✅ Health checks
- ✅ Email configuration test

### `migrate_database.sh`
Database-only operations:
- ✅ Database connection test
- ✅ Migration status check
- ✅ Apply pending migrations
- ✅ Conflict detection

### `rollback_database.sh`
Database rollback operations:
- ✅ Rollback to previous migration
- ✅ Rollback to specific revision
- ✅ Rollback to base (⚠️ drops all data)

## Manual Deployment Steps

If you prefer manual deployment:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Load environment variables
export $(grep -v '^#' .env | xargs)

# 3. Run migrations
alembic upgrade head

# 4. Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Production Considerations

### Security
- Use strong, unique passwords
- Generate a long, random SECRET_KEY
- Keep .env file secure (not in git)
- Use HTTPS in production
- Configure firewall rules

### Performance
- Use multiple workers: `--workers 4`
- Configure Nginx as reverse proxy
- Enable Redis for caching
- Monitor memory usage

### Monitoring
- Check logs: `tail -f logs/app.log`
- Monitor database connections
- Set up health check endpoints
- Configure log rotation

## Nginx Configuration (Optional)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Systemd Service (Optional)

Create `/etc/systemd/system/prozlab-backend.service`:

```ini
[Unit]
Description=ProzLab Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/prozlab_backend
Environment=PATH=/path/to/prozlab_backend/venv/bin
ExecStart=/path/to/prozlab_backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable prozlab-backend
sudo systemctl start prozlab-backend
```

## Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U proz_user -d prozlab_db
```

**Migration Conflicts**
```bash
# Check migration status
alembic current
alembic heads

# Resolve conflicts
alembic merge -m "merge migrations" <revision1> <revision2>
```

**Email Not Working**
```bash
# Test email configuration
curl http://localhost:8000/api/v1/auth/email/status

# Check SMTP credentials in .env
```

**Application Won't Start**
```bash
# Check logs
tail -f logs/app.log

# Test manually
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Logs

- Application logs: `logs/app.log`
- Nginx logs: `/var/log/nginx/`
- System logs: `journalctl -u prozlab-backend`

## Maintenance

### Regular Tasks
- Monitor disk space
- Check application health
- Review logs for errors
- Update dependencies
- Backup database

### Updates
```bash
# Pull latest changes
git pull origin main

# Run migrations
./migrate_database.sh

# Restart application
pkill -f uvicorn
./deploy_production.sh
```

## Support

For issues or questions:
- Check logs first
- Review this documentation
- Test with manual deployment
- Contact support team

---

**Note**: Always test deployments in a staging environment before production!
