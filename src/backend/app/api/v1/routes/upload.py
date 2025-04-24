import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.v1.schemas.upload import UploadResponse
from app.core.config import app_config
from app.core.logging import logger

from ..helpers.file_helpers import is_file_type_allowed

router = APIRouter()

UPLOAD_DIR = app_config.settings.UPLOAD_DIR
ALLOWED_EXTENSIONS = app_config.settings.allowed_extensions
MAX_FILE_SIZE = app_config.settings.MAX_FILE_SIZE

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", summary="Upload a file")
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
) -> UploadResponse:
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required",
            )

        logger.info(f"Starting upload for file: {file.filename}")

        # Validate file type
        if not is_file_type_allowed(file, ALLOWED_EXTENSIONS):
            logger.error(f"Invalid file type for: {file.filename}")
            allowed_types = ", ".join(ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {allowed_types}",
            )

        # Validate file size
        if file.size and file.size > MAX_FILE_SIZE:
            logger.error(
                f"File size {file.size} bytes exceeds limit for: {file.filename}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"File size too large. Maximum size: {MAX_FILE_SIZE} bytes",
            )

        # Save file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        logger.info(f"File uploaded successfully: {file.filename}")
        return UploadResponse(
            filename=file.filename,
            message="File uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while uploading file",
        )
