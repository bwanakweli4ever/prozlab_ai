# app/modules/proz/services/media_service.py
from typing import Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path
import shutil

from app.config.settings import settings


class MediaService:
    """Media service for file uploads"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.profile_images_dir = self.upload_dir / "profile_images"
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(exist_ok=True)
        self.profile_images_dir.mkdir(exist_ok=True)
    
    def get_upload_status(self) -> Dict[str, Any]:
        """Get upload service status"""
        return {
            "service": "Media Upload Service",
            "status": "active",
            "upload_directory": str(self.upload_dir),
            "max_file_size": "5MB",
            "allowed_types": ["image/jpeg", "image/png", "image/gif", "image/webp"]
        }
    
    async def upload_profile_image(self, db: Session, user_id: str, file: UploadFile) -> Dict[str, Any]:
        """Upload and save profile image"""
        try:
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if file.filename else 'jpg'
            file_name = f"{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = self.profile_images_dir / file_name
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create file URL
            file_url = f"/static/profile_images/{file_name}"
            
            # TODO: Update user's profile with new image URL in database
            print(f"📁 Saved profile image: {file_path}")
            print(f"🔗 Image URL: {file_url}")
            
            return {
                "success": True,
                "message": "Profile image uploaded successfully",
                "file_name": file_name,
                "file_url": file_url,
                "file_size": file_path.stat().st_size
            }
            
        except Exception as e:
            print(f"❌ Error uploading file: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")
    
    def delete_profile_image(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Delete user's profile image"""
        try:
            # Find user's current profile image
            # This is a simplified approach - in production, you'd query the database
            user_images = list(self.profile_images_dir.glob(f"{user_id}_*"))
            
            if not user_images:
                return {
                    "success": True,
                    "message": "No profile image to delete"
                }
            
            # Delete all user images (in case there are multiple)
            deleted_count = 0
            for image_path in user_images:
                try:
                    image_path.unlink()
                    deleted_count += 1
                    print(f"🗑️ Deleted image: {image_path}")
                except Exception as e:
                    print(f"❌ Error deleting {image_path}: {str(e)}")
            
            # TODO: Update user's profile in database to remove image URL
            
            return {
                "success": True,
                "message": f"Deleted {deleted_count} profile image(s)",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            print(f"❌ Error deleting profile images: {str(e)}")
            raise Exception(f"Failed to delete images: {str(e)}")
    
    def get_profile_image_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about user's profile image"""
        try:
            user_images = list(self.profile_images_dir.glob(f"{user_id}_*"))
            
            if not user_images:
                return {
                    "has_image": False,
                    "message": "No profile image found"
                }
            
            # Get the most recent image
            latest_image = max(user_images, key=lambda p: p.stat().st_mtime)
            
            return {
                "has_image": True,
                "file_name": latest_image.name,
                "file_url": f"/static/profile_images/{latest_image.name}",
                "file_size": latest_image.stat().st_size,
                "created_at": latest_image.stat().st_ctime
            }
            
        except Exception as e:
            print(f"❌ Error getting image info: {str(e)}")
            return {
                "has_image": False,
                "error": str(e)
            }