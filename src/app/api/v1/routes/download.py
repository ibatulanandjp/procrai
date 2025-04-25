import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import app_config
from app.core.logging import logger

router = APIRouter()


@router.get("/", summary="Download translated document")
async def get_translated_doc(
    filename: str,
) -> FileResponse:
    """
    Download the translated document.

    Args:
        filename: Name of the file to download
    Returns:
        FileResponse: Response containing the file
    Raises:
        HTTPException: If the file is not found
    """
    try:
        file_path = os.path.join(app_config.settings.OUTPUT_DIR, filename)
        logger.info(f"Retrieving result file: {filename}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        logger.info(f"Successfully retrieved file: {filename}")
        return FileResponse(file_path, media_type="application/pdf", filename=filename)
    except Exception as e:
        logger.error(f"Error retrieving file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")
