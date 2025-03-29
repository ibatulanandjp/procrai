import os

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.services.ocr_service import OcrService
from app.core.config import app_config

from ..schemas.ocr import OcrResponse

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
        elements, page_count = await ocr_service.extract_text(file_path)
        return OcrResponse(
            elements=elements,
            page_count=page_count,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from file: {str(e)}",
        )
