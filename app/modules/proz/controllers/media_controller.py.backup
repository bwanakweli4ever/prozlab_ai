# app/modules/proz/controllers/media_controller.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.schemas.files import (
    FileUploadResponse, ProfileImageResponse, ProfileImageUpdateRequest
)
from app.services.file_service import FileService

router = APIRouter()
auth_service = AuthService()
file_service = FileService()


@router.post("/upload-profile-image", response_model=FileUploadResponse)
async def upload_profile_image(
    file: UploadFile = File(..., description="Profile image file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Upload a profile image for the current user.
    Supports JPG, JPEG, PNG, GIF formats up to 5MB.
    """
    # Get user's profile
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found. Please create your profile first."
        )
    
    # Upload and process image
    result = file_service.upload_profile_image(file, profile.id)
    
    if not result["success"]:
        if result.get("error_code") == "INVALID_FILE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    # Update profile with new image URL
    old_image_url = profile.profile_image_url
    profile.profile_image_url = result["primary_url"]
    db.commit()
    db.refresh(profile)
    
    # Clean up old image if it exists
    if old_image_url:
        old_filename = old_image_url.split('/')[-1]
        file_service.delete_profile_image(old_filename)
    
    return FileUploadResponse(
        success=result["success"],
        message=result["message"],
        file_url=result["primary_url"],
        file_name=result["file_name"],
        file_size=result["file_size"]
    )


@router.delete("/delete-profile-image", response_model=ProfileImageResponse)
async def delete_profile_image(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Delete the current user's profile image.
    """
    # Get user's profile
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found."
        )
    
    if not profile.profile_image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile image to delete."
        )
    
    # Extract filename from URL
    filename = profile.profile_image_url.split('/')[-1]
    
    # Delete image files
    result = file_service.delete_profile_image(filename)
    
    # Update profile regardless of file deletion result
    profile.profile_image_url = None
    db.commit()
    db.refresh(profile)
    
    return ProfileImageResponse(
        success=True,
        message="Profile image deleted successfully",
        profile_image_url=None
    )


@router.get("/profile-image-info")
async def get_profile_image_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Get information about the current user's profile image.
    """
    # Get user's profile
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found."
        )
    
    if not profile.profile_image_url:
        return {
            "has_image": False,
            "message": "No profile image set"
        }
    
    # Extract filename and get image info
    filename = profile.profile_image_url.split('/')[-1]
    image_info = file_service.get_image_info(filename)
    
    if image_info:
        return {
            "has_image": True,
            "current_url": profile.profile_image_url,
            "image_info": image_info
        }
    else:
        # Image referenced in DB but file doesn't exist
        profile.profile_image_url = None
        db.commit()
        
        return {
            "has_image": False,
            "message": "Image file not found, reference cleared"
        }


@router.post("/update-profile-image-url", response_model=ProfileImageResponse)
async def update_profile_image_url(
    request: ProfileImageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Update profile image URL (for external image URLs or cloud storage).
    """
    # Get user's profile
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found."
        )
    
    # Update profile image URL
    old_image_url = profile.profile_image_url
    profile.profile_image_url = request.image_url
    db.commit()
    db.refresh(profile)
    
    # If old image was locally stored, clean it up
    if old_image_url and old_image_url.startswith('/static/profile_images/'):
        old_filename = old_image_url.split('/')[-1]
        file_service.delete_profile_image(old_filename)
    
    return ProfileImageResponse(
        success=True,
        message="Profile image URL updated successfully",
        profile_image_url=profile.profile_image_url
    )


# Admin endpoints for image management
@router.post("/admin/cleanup-orphaned-images")
async def cleanup_orphaned_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Admin endpoint to clean up orphaned image files.
    Removes image files that are no longer referenced in the database.
    """
    # Get all valid image filenames from database
    profiles_with_images = db.query(ProzProfile).filter(
        ProzProfile.profile_image_url.isnot(None)
    ).all()
    
    valid_filenames = []
    for profile in profiles_with_images:
        if profile.profile_image_url and profile.profile_image_url.startswith('/static/profile_images/'):
            filename = profile.profile_image_url.split('/')[-1]
            valid_filenames.append(filename)
    
    # Perform cleanup
    result = file_service.cleanup_orphaned_images(valid_filenames)
    
    return {
        "success": result["success"],
        "message": result["message"],
        "deleted_count": result.get("deleted_count", 0),
        "valid_images_count": len(valid_filenames)
    }