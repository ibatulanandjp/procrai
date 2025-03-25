from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.translation import TranslationRequest, TranslationResponse
from app.api.v1.services.translation_service import TranslationService

router = APIRouter()


@router.post("/", summary="Translate text from one language to another")
async def translate(
    request: TranslationRequest,
    translation_service: TranslationService = Depends(TranslationService),
) -> TranslationResponse:
    try:
        translated_text = await translation_service.translate(
            request.text, request.src_lang, request.target_lang
        )
        return TranslationResponse(
            translated_text=translated_text,
            src_lang=request.src_lang,  # TODO: Add language detection
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to translate text: {str(e)}"
        )
