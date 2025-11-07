# app/services/file_service.py
import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = getattr(settings, 'MAX_FILE_SIZE', 5 * 1024 * 1024)  # 5MB default
UPLOAD_DIR = getattr(settings, 'UPLOAD_DIR', 'uploads')
ALLOWED_IMAGE_TYPES = settings.ALLOWED_IMAGE_TYPES

# Image sizes for different use cases
IMAGE_SIZES = {
    'thumbnail': (150, 150),
    'medium': (400, 400),
    'large': (800, 800)
}


class FileService:
    def __init__(self):
        self.upload_dir = Path(UPLOAD_DIR)
        self.profile_images_dir = self.upload_dir / 'profile_images'
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create upload directories if they don't exist"""
        self.upload_dir.mkdir(exist_ok=True)
        self.profile_images_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different image sizes
        for size_name in IMAGE_SIZES.keys():
            (self.profile_images_dir / size_name).mkdir(exist_ok=True)
    
    def _validate_image_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate uploaded image file"""
        # Check file size
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            if file_size > MAX_FILE_SIZE:
                return {
                    "valid": False,
                    "error": f"File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / (1024*1024):.1f}MB)"
                }
        
        # Check file extension
        if not file.filename:
            return {
                "valid": False,
                "error": "No filename provided"
            }
        
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ALLOWED_IMAGE_TYPES:
            return {
                "valid": False,
                "error": f"File type '{file_extension}' not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
            }
        
        # Check MIME type
        if file.content_type and not file.content_type.startswith('image/'):
            return {
                "valid": False,
                "error": f"Invalid content type: {file.content_type}"
            }
        
        return {"valid": True}
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension"""
        file_extension = original_filename.split('.')[-1].lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{file_extension}"
    
    def _resize_image(self, image_path: Path, size: tuple, output_path: Path):
        """Resize image to specified dimensions"""
        try:
            with Image.open(image_path) as img:
                # Convert RGBA to RGB if necessary (for JPEG)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize maintaining aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Create a square image with padding if needed
                new_img = Image.new('RGB', size, (255, 255, 255))
                paste_x = (size[0] - img.size[0]) // 2
                paste_y = (size[1] - img.size[1]) // 2
                new_img.paste(img, (paste_x, paste_y))
                
                # Save with optimization
                new_img.save(output_path, 'JPEG', quality=85, optimize=True)
                
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            raise
    
    def upload_profile_image(self, file: UploadFile, user_id: str) -> Dict[str, Any]:
        """Upload and process profile image"""
        try:
            # Validate file
            validation = self._validate_image_file(file)
            if not validation["valid"]:
                return {
                    "success": False,
                    "message": validation["error"],
                    "error_code": "INVALID_FILE"
                }
            
            # Generate unique filename
            unique_filename = self._generate_unique_filename(file.filename)
            original_path = self.profile_images_dir / unique_filename
            
            # Save original file
            with open(original_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = original_path.stat().st_size
            
            # Create different sized versions
            image_urls = {}
            for size_name, dimensions in IMAGE_SIZES.items():
                size_dir = self.profile_images_dir / size_name
                size_path = size_dir / unique_filename
                
                self._resize_image(original_path, dimensions, size_path)
                
                # Generate URL (adjust based on your serving setup)
                image_urls[size_name] = f"/uploads/profile_images/{size_name}/{unique_filename}"
            
            # Clean up original if we only want processed versions
            # os.remove(original_path)  # Uncomment if you don't want to keep originals
            
            logger.info(f"Profile image uploaded successfully for user {user_id}: {unique_filename}")
            
            return {
                "success": True,
                "message": "Profile image uploaded successfully",
                "file_name": unique_filename,
                "file_size": file_size,
                "original_filename": file.filename,
                "image_urls": image_urls,
                "primary_url": image_urls["medium"]  # Default size for profiles
            }
            
        except Exception as e:
            logger.error(f"Error uploading profile image: {str(e)}")
            return {
                "success": False,
                "message": "Failed to upload image",
                "error_code": "UPLOAD_FAILED",
                "error_details": str(e)
            }
    
    def delete_profile_image(self, filename: str) -> Dict[str, Any]:
        """Delete profile image and all its variants"""
        try:
            deleted_files = []
            
            # Delete all size variants
            for size_name in IMAGE_SIZES.keys():
                size_path = self.profile_images_dir / size_name / filename
                if size_path.exists():
                    size_path.unlink()
                    deleted_files.append(str(size_path))
            
            # Delete original if it exists
            original_path = self.profile_images_dir / filename
            if original_path.exists():
                original_path.unlink()
                deleted_files.append(str(original_path))
            
            if deleted_files:
                logger.info(f"Deleted profile image files: {deleted_files}")
                return {
                    "success": True,
                    "message": "Profile image deleted successfully",
                    "deleted_files": deleted_files
                }
            else:
                return {
                    "success": False,
                    "message": "Image file not found",
                    "error_code": "FILE_NOT_FOUND"
                }
                
        except Exception as e:
            logger.error(f"Error deleting profile image: {str(e)}")
            return {
                "success": False,
                "message": "Failed to delete image",
                "error_code": "DELETE_FAILED",
                "error_details": str(e)
            }
    
    def get_image_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about an uploaded image"""
        try:
            # Check if file exists in any size variant
            available_sizes = {}
            for size_name in IMAGE_SIZES.keys():
                size_path = self.profile_images_dir / size_name / filename
                if size_path.exists():
                    stat = size_path.stat()
                    available_sizes[size_name] = {
                        "path": str(size_path),
                        "url": f"/static/profile_images/{size_name}/{filename}",
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    }
            
            if available_sizes:
                return {
                    "filename": filename,
                    "available_sizes": available_sizes,
                    "primary_url": available_sizes.get("medium", {}).get("url")
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting image info: {str(e)}")
            return None
    
    def cleanup_orphaned_images(self, valid_filenames: List[str]) -> Dict[str, Any]:
        """Clean up images that are no longer referenced in the database"""
        try:
            deleted_count = 0
            
            for size_name in IMAGE_SIZES.keys():
                size_dir = self.profile_images_dir / size_name
                if size_dir.exists():
                    for image_file in size_dir.glob("*"):
                        if image_file.name not in valid_filenames:
                            image_file.unlink()
                            deleted_count += 1
            
            return {
                "success": True,
                "message": f"Cleanup completed. Deleted {deleted_count} orphaned files.",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {
                "success": False,
                "message": "Cleanup failed",
                "error_code": "CLEANUP_FAILED",
                "error_details": str(e)
            }