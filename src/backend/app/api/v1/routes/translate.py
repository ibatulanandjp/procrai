from fastapi import APIRouter, Depends, HTTPException

from app.core.logging import logger

from ..schemas.translation import TranslationRequest, TranslationResponse
from ..services.translation_service import TranslationService

router = APIRouter()


@router.post("/", summary="Translate document elements with layout preservation")
async def translate(
    request: TranslationRequest,
    translation_service: TranslationService = Depends(TranslationService),
) -> TranslationResponse:
    try:
        logger.info(
            f"Starting translation from {request.src_lang} to {request.target_lang}"
        )
        result = await translation_service.translate_elements(request)

        logger.info("Translation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to translate document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to translate document: {str(e)}",
        )
