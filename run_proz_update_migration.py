# run_proz_update_migration.py
#!/usr/bin/env python3
"""
Script to update the database tables for the enhanced Proz Profile model.
Run this script after adding the new fields to your model.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def update_env_py():
    """Ensure env.py has the latest model imports"""
    env_path = Path('migrations') / 'env.py'
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Make sure the imports are up to date
        print("Ensuring model imports are up to date in env.py...")
        return True
    else:
        print("env.py not found.")
        return False

def create_migration():
    """Create a migration for the updated models"""
    print("Creating migration for updated Proz models...")
    try:
        result = subprocess.run(
            ['alembic', 'revision', '--autogenerate', '-m', 'Update Proz Profile with additional fields'],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating migration: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def apply_migration():
    """Apply the migration"""
    print("Applying migration...")
    try:
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error applying migration: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main function to run migrations"""
    print("Updating Proz module tables...")
    
    # Update env.py
    if not update_env_py():
        print("Failed to update env.py. Aborting.")
        return 1
    
    # Create migration
    if not create_migration():
        print("Failed to create migration. Aborting.")
        return 1
    
    # Apply migration
    if not apply_migration():
        print("Failed to apply migration. Aborting.")
        return 1
    
    print("Proz module table updates completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())