from fastapi import APIRouter, File, UploadFile
from fastapi.exceptions import HTTPException

from app.api.v1.schemas.upload import UploadResponse
from app.api.v1.services.upload_service import upload_service

router = APIRouter()


@router.post("/", summary="Upload a file")
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
) -> UploadResponse:
    """
    Upload a file to the server.

    Args:
        file: The file to upload
    Returns:
        UploadResponse: Response containing upload status
    Raises:
        HTTPException: If the file upload fails
    """
    try:
        return await upload_service.upload_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}",
        )
