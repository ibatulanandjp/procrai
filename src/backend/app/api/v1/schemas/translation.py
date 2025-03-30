from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from app.api.v1.schemas.document import DocumentElement


class LanguageCode(str, Enum):
    ENGLISH = "en"
    JAPANESE = "ja"


class TranslationRequest(BaseModel):
    elements: List[DocumentElement] = Field(
        ..., description="List of elements to translate"
    )
    src_lang: LanguageCode = Field(LanguageCode.ENGLISH, description="Source language")
    target_lang: LanguageCode = Field(
        LanguageCode.JAPANESE, description="Target language"
    )


class TranslationResponse(BaseModel):
    translated_elements: List[DocumentElement] = Field(
        ..., description="List of translated elements"
    )
