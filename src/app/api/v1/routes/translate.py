from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.translation import TranslationRequest, TranslationResponse
from app.api.v1.services.translation_service import TranslationService
from app.core.logging import logger

router = APIRouter()


@router.post("/", summary="Translate document elements with layout preservation")
async def translate(
    request: TranslationRequest,
    translation_service: TranslationService = Depends(TranslationService),
) -> TranslationResponse:
    """
    Translate document elements while preserving layout.

    Args:
        request: TranslationRequest object containing source and target languages
    Returns:
        TranslationResponse: Response containing translation status
    Raises:
        HTTPException: If the translation fails
    """
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
