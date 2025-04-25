import os

from fastapi import HTTPException, UploadFile

from app.api.v1.helpers.file_helpers import is_file_type_allowed
from app.api.v1.schemas.upload import UploadResponse
from app.core.config import app_config
from app.core.logging import logger


class UploadService:
    def __init__(self):
        self.upload_dir = app_config.settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

        self.allowed_extensions = app_config.settings.allowed_extensions
        self.max_file_size = app_config.settings.MAX_FILE_SIZE

    async def upload_file(self, file: UploadFile) -> UploadResponse:
        """
        Handle file upload with validation and storage.

        Args:
            file: The file to upload
        Returns:
            UploadResponse: Response containing upload status
        """
        try:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Filename is required",
                )

            logger.info(f"Starting upload for file: {file.filename}")

            # Validate file type
            if not is_file_type_allowed(file, self.allowed_extensions):
                logger.error(f"Invalid file type for: {file.filename}")
                allowed_types = ", ".join(self.allowed_extensions)
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed. Allowed types: {allowed_types}",
                )

            # Validate file size
            if file.size and file.size > self.max_file_size:
                logger.error(
                    f"File size {file.size} bytes exceeds limit for: {file.filename}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"File size too large. Max size: {self.max_file_size} bytes",
                )

            # Save file
            file_path = os.path.join(self.upload_dir, file.filename)
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


upload_service = UploadService()
