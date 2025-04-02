from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.translation import TranslationRequest, TranslationResponse
from app.api.v1.services.translation_service import TranslationService

router = APIRouter()


@router.post("/", summary="Translate document elements with layout preservation")
async def translate(
    request: TranslationRequest,
    translation_service: TranslationService = Depends(TranslationService),
) -> TranslationResponse:
    try:
        return await translation_service.translate_elements(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to translate document: {str(e)}",
        )
