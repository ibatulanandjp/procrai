import os

from fastapi import HTTPException

from app.core.config import app_config
from app.core.logging import logger

from app.api.v1.schemas.translation import LanguageCode, TranslationRequest
from app.api.v1.services.ocr_service import OcrService
from app.api.v1.services.reconstruction_service import ReconstructionService
from app.api.v1.services.translation_service import TranslationService

UPLOAD_DIR = app_config.settings.UPLOAD_DIR


class WorkflowService:
    def __init__(self):
        self.ocr_service = OcrService()
        self.translate_service = TranslationService()
        self.reconstruct_service = ReconstructionService()

    async def process_workflow(
        self, filename: str, src_lang: str, target_lang: str
    ) -> str:
        """
        Process a document through the complete workflow:
        OCR -> Translation -> Reconstruction

        Returns the final PDF filename.
        """
        try:
            logger.info(f"Starting document processing workflow for {filename}")
            filepath = os.path.join(UPLOAD_DIR, filename)

            # Step 1: OCR
            logger.info("Starting OCR processing")
            extracted_elements, _ = await self.ocr_service.extract_text(filepath)

            # Step 2: Translate
            logger.info("Starting translation")
            translation_request = TranslationRequest(
                elements=extracted_elements,
                src_lang=LanguageCode(src_lang),
                target_lang=LanguageCode(target_lang),
            )
            translated_elements = await self.translate_service.translate_elements(
                translation_request
            )

            # Step 3: Reconstruction
            logger.info("Starting PDF reconstruction")
            output_filepath = await self.reconstruct_service.reconstruct_pdf(
                elements=translated_elements.translated_elements,
                original_filename=filename,
            )

            logger.info(f"PDF reconstructed successfully at {output_filepath}")
            return output_filepath

        except Exception as e:
            logger.error(f"Error during workflow processing: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Workflow processing failed: {str(e)}"
            )
