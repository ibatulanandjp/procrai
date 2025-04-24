from pathlib import Path
from typing import List, Tuple, Union

from fastapi import HTTPException

from app.core.logging import logger

from ..schemas.document import DocumentElement
from .ocr.image_service import image_service
from .ocr.pdf_service import pdf_service


class OcrService:
    def __init__(self):
        self.image_service = image_service
        self.pdf_service = pdf_service

    async def extract_text(
        self, file_path: Union[Path, str]
    ) -> Tuple[List[DocumentElement], int]:
        """
        Extract text and layout information from a PDF or image file.

        Args:
            file_path: Path to the PDF or image file
        Returns:
            Tuple[List[DocumentElement], int]: Extracted elements and page count
        """
        file_path = Path(file_path)

        try:
            logger.info(f"Starting OCR processing for file: {file_path}")
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                logger.debug("Processing image file")
                with open(file_path, "rb") as f:
                    return await self.image_service.process_image(f.read())
            elif file_path.suffix.lower() == ".pdf":
                logger.debug("Processing PDF file")
                return await self.pdf_service.process_pdf(file_path)
            else:
                logger.error(f"Unsupported file type: {file_path.suffix}")
                raise ValueError("Unsupported file type for OCR")
        except Exception as e:
            logger.error(f"Failed to process file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}",
            )


ocr_service = OcrService()
