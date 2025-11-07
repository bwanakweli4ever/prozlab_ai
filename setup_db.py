#!/usr/bin/env python3
"""
Database initialization script for the FastAPI Modular Backend.
This script sets up Alembic for migrations and creates the initial migration.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent))

# Corrected imports - import Base from the right location
from app.config.database import engine
from app.database.base_class import Base  # Import Base from base_class instead
from app.modules.auth.models.user import User  # Import all models

def init_alembic():
    """Initialize Alembic for migrations if not already set up."""
    if not os.path.exists('alembic'):
        print("Initializing Alembic for database migrations...")
        subprocess.run(['alembic', 'init', 'migrations'], check=True)
        
        # Update alembic.ini with the correct database URL
        with open('alembic.ini', 'r') as f:
            content = f.read()
        
        # Replace SQLAlchemy URL
        from app.config.settings import settings
        content = content.replace(
            'sqlalchemy.url = driver://user:pass@localhost/dbname',
            f'sqlalchemy.url = {settings.DATABASE_URL}'
        )
        
        with open('alembic.ini', 'w') as f:
            f.write(content)
        
        # Update env.py to import models and use our Base
        env_path = Path('migrations') / 'env.py'
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Add import for our Base and models
        import_stmt = """
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database.base_class import Base  # Import Base from the right location
from app.modules.auth.models.user import User  # Import all models
"""
        
        # Replace the target_metadata = None line
        content = content.replace(
            'target_metadata = None',
            'target_metadata = Base.metadata'
        )
        
        # Add imports at the beginning
        content = import_stmt + content
        
        with open(env_path, 'w') as f:
            f.write(content)

def create_tables():
    """Create database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

def create_initial_migration():
    """Create the initial database migration."""
    print("Creating initial migration...")
    subprocess.run(['alembic', 'revision', '--autogenerate', '-m', 'Initial migration'], check=True)
    print("Applying migration...")
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)

def setup_superuser():
    """Create a superuser if it doesn't exist."""
    from sqlalchemy.orm import Session
    from app.core.security import get_password_hash
    from app.modules.auth.repositories.user_repository import UserRepository
    
    print("Checking for superuser...")
    
    # Create a session
    db = Session(engine)
    
    # Check if superuser exists
    user_repo = UserRepository()
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    admin = user_repo.get_by_email(db, email=admin_email)
    
    if not admin:
        print(f"Creating superuser with email: {admin_email}")
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        # Create superuser
        user_data = {
            "email": admin_email,
            "password": admin_password,
            "first_name": "Admin",
            "last_name": "User",
            "is_superuser": True,
            "is_active": True
        }
        
        # Use repository to create user
        user_repo.create(db, obj_in=user_data)
        print("Superuser created successfully.")
    else:
        print("Superuser already exists.")
    
    db.close()

if __name__ == '__main__':
    print("Setting up database for FastAPI Modular Backend")
    init_alembic()
    create_initial_migration()
    setup_superuser()
    print("Database setup complete!")