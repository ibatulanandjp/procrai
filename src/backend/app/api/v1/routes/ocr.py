import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.v1.services.ocr_service import ocr_service
from app.core.config import app_config

router = APIRouter()

UPLOAD_DIR = app_config.settings.UPLOAD_DIR


@router.get("/", summary="Extract text from a PDF/image file")
async def ocr(filename: str) -> JSONResponse:
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    try:
        extracted_text = ocr_service.extract_text(file_path)
        return JSONResponse(
            content={"filename": filename, "extracted_text": extracted_text}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from file: {str(e)}",
        )
