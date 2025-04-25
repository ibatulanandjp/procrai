import os

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.ocr import OcrResponse
from app.api.v1.services.ocr_service import OcrService
from app.core.config import app_config
from app.core.logging import logger

router = APIRouter()

UPLOAD_DIR = app_config.settings.UPLOAD_DIR


@router.get("/", summary="Extract text from a PDF/image file")
async def ocr(
    filename: str,
    ocr_service: OcrService = Depends(OcrService),
) -> OcrResponse:
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    try:
        logger.debug(f"OCR request details: filename={filename}")
        elements, page_count = await ocr_service.extract_text(file_path)

        logger.info("OCR processing completed successfully")
        return OcrResponse(
            elements=elements,
            page_count=page_count,
        )
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from file: {str(e)}",
        )
