"""File upload endpoints for nomination images."""
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.auth.rbac import RequireManager
from app.config import get_settings
from app.db.session import get_session
from app.models.domain import User
from sqlalchemy.orm import Session

router = APIRouter()
settings = get_settings()

# Allowed image extensions
ALLOWED_EXTENSIONS = {ext.lower() for ext in settings.upload_allowed_extensions.split(",")}


def ensure_upload_dir():
    """Ensure upload directory exists."""
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    # Check file extension
    filename = file.filename or ""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check content type
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )


@router.post("/uploads/images", response_class=JSONResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> dict:
    """
    Upload an image file for nomination criteria.
    
    Returns the URL to access the uploaded image.
    """
    # Validate file
    validate_image_file(file)
    
    # Check file size
    max_size_bytes = settings.upload_max_size_mb * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.upload_max_size_mb}MB"
        )
    
    # Generate unique filename
    ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Ensure upload directory exists
    upload_path = ensure_upload_dir()
    file_path = upload_path / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Generate URL
    image_url = f"{settings.upload_base_url}/{unique_filename}"
    
    return {
        "url": image_url,
        "filename": unique_filename,
        "size": len(file_content),
        "content_type": file.content_type
    }


@router.post("/uploads/images/batch", response_class=JSONResponse)
async def upload_images_batch(
    files: List[UploadFile] = File(..., description="Multiple image files to upload"),
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> dict:
    """
    Upload multiple image files for nomination criteria.
    
    Returns URLs to access the uploaded images.
    """
    if len(files) > 10:  # Limit batch size
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per batch upload"
        )
    
    upload_path = ensure_upload_dir()
    max_size_bytes = settings.upload_max_size_mb * 1024 * 1024
    results = []
    
    for file in files:
        try:
            # Validate file
            validate_image_file(file)
            
            # Check file size
            file_content = await file.read()
            if len(file_content) > max_size_bytes:
                results.append({
                    "filename": file.filename,
                    "error": f"File size exceeds maximum allowed size of {settings.upload_max_size_mb}MB"
                })
                continue
            
            # Generate unique filename
            ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = upload_path / unique_filename
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Generate URL
            image_url = f"{settings.upload_base_url}/{unique_filename}"
            
            results.append({
                "filename": file.filename,
                "url": image_url,
                "size": len(file_content),
                "content_type": file.content_type
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "results": results,
        "success_count": len([r for r in results if "error" not in r]),
        "error_count": len([r for r in results if "error" in r])
    }

