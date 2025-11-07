#!/usr/bin/env python3
"""
Script to create the complete directory structure for the Proz module
"""

import os
from pathlib import Path

def create_directory(path):
    """Create a directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_file(path, content=""):
    """Create a file with content if it doesn't exist"""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(content)
        print(f"Created file: {path}")
    else:
        print(f"File already exists: {path}")

def setup_proz_module():
    """Set up the complete directory structure for the Proz module"""
    # Base paths
    root_dir = Path("app")
    modules_dir = root_dir / "modules"
    proz_dir = modules_dir / "proz"
    
    # Create the main directories
    create_directory(root_dir)
    create_directory(modules_dir)
    create_directory(proz_dir)
    
    # Create __init__.py files
    create_file(root_dir / "__init__.py")
    create_file(modules_dir / "__init__.py")
    create_file(proz_dir / "__init__.py")
    
    # Create module subdirectories and their __init__.py files
    subdirs = [
        "controllers",
        "models",
        "schemas",
        "services",
        "repositories"
    ]
    
    for subdir in subdirs:
        subdir_path = proz_dir / subdir
        create_directory(subdir_path)
        create_file(subdir_path / "__init__.py")
    
    # Create routes.py
    create_file(proz_dir / "routes.py", 
        """from fastapi import APIRouter

# This is a placeholder that will be replaced with your actual implementation
router = APIRouter()
"""
    )
    
    print("\nDirectory structure for Proz module has been created successfully.")
    print("Now you can place your implementation files in the appropriate directories.")

if __name__ == "__main__":
    setup_proz_module()