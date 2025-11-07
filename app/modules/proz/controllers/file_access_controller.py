# app/modules/proz/controllers/file_access_controller.py
from typing import Any
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from fastapi.responses import FileResponse
from pathlib import Path
import os

from app.config.settings import settings

router = APIRouter()

@router.get("/profile-images/{filename}")
async def get_profile_image(
    filename: str = FastAPIPath(..., description="Image filename")
) -> Any:
    """
    Get a profile image file.
    Returns the actual file for download/display.
    """
    # Construct file path
    file_path = Path(settings.UPLOAD_DIR) / "profile_images" / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Check if it's actually a file (not a directory)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid file"
        )
    
    # Get file info for headers
    file_size = file_path.stat().st_size
    
    # Return the file
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",  # You can make this dynamic based on file extension
        filename=filename,
        headers={
            "Content-Length": str(file_size),
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        }
    )

@router.get("/profile-images/{size}/{filename}")
async def get_profile_image_sized(
    size: str = FastAPIPath(..., description="Image size: thumbnail, medium, large"),
    filename: str = FastAPIPath(..., description="Image filename")
) -> Any:
    """
    Get a profile image file in specific size.
    """
    # Validate size
    valid_sizes = ["thumbnail", "medium", "large"]
    if size not in valid_sizes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid size. Must be one of: {', '.join(valid_sizes)}"
        )
    
    # Construct file path
    file_path = Path(settings.UPLOAD_DIR) / "profile_images" / size / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found in {size} size"
        )
    
    # Determine media type based on file extension
    extension = filename.lower().split('.')[-1]
    media_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    media_type = media_type_map.get(extension, 'image/jpeg')
    
    # Get file info for headers
    file_size = file_path.stat().st_size
    
    # Return the file
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Length": str(file_size),
            "Cache-Control": "public, max-age=3600"
        }
    )