#!/usr/bin/env python3
"""
Script to create and apply migrations for the Proz Profile module.
Run this script after adding the Proz module to your project.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def update_env_py():
    """Update env.py to import all models"""
    env_path = Path('migrations') / 'env.py'
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Check if Proz models are already imported
        if 'from app.modules.proz.models.proz import' not in content:
            # Find where to insert imports
            import_section = content.find('from app.database.base_class import Base')
            if import_section == -1:
                print("Could not find where to insert imports in env.py")
                return False
            
            # Add Proz model imports after Base import
            import_line = "from app.modules.proz.models.proz import ProzProfile, Specialty, ProzSpecialty, Review, VerificationStatus"
            # Find the next line after Base import
            next_line = content.find('\n', import_section)
            
            # Insert imports
            updated_content = content[:next_line] + f"\n{import_line}" + content[next_line:]
            
            # Write updated content
            with open(env_path, 'w') as f:
                f.write(updated_content)
            
            print("Updated env.py with Proz model imports.")
        else:
            print("Proz models already imported in env.py.")
        
        # Ensure target_metadata is properly set
        if 'target_metadata = None' in content:
            # Replace None with Base.metadata
            updated_content = content.replace('target_metadata = None', 'target_metadata = Base.metadata')
            
            # Write updated content
            with open(env_path, 'w') as f:
                f.write(updated_content)
            
            print("Updated target_metadata in env.py.")
        
        return True
    else:
        print("env.py not found.")
        return False

def create_migration():
    """Create a migration for the Proz models"""
    print("Creating migration for Proz models...")
    try:
        result = subprocess.run(
            ['alembic', 'revision', '--autogenerate', '-m', 'Add Proz Profile models'],
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
    print("Setting up Proz module migrations...")
    
    # Skip Alembic initialization since it already exists
    print("Alembic already initialized. Skipping initialization step.")
    
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
    
    print("Proz module migrations completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())