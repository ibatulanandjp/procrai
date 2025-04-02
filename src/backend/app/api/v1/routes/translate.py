from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.translation import TranslationRequest, TranslationResponse
from app.api.v1.services.translation_service import TranslationService

router = APIRouter()


@router.post("/", summary="Translate document elements with layout preservation")
async def translate_document(
    request: TranslationRequest,
    translation_service: TranslationService = Depends(TranslationService),
) -> TranslationResponse:
    """
    Translate document elements while preserving layout and formatting.

    Args:
        request: TranslationRequest containing elements to translate
        translation_service: Injected translation service

    Returns:
        TranslationResponse containing the translated elements

    Raises:
        HTTPException: If translation fails
    """
    try:
        return await translation_service.translate_elements(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to translate document: {str(e)}",
        )
