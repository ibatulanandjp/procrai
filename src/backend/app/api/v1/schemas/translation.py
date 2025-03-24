from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LanguageCode(str, Enum):
    ENGLISH = "en"
    JAPANESE = "ja"


class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to be translated")
    src_lang: LanguageCode = Field(LanguageCode.ENGLISH, description="Source language")
    target_lang: LanguageCode = Field(
        LanguageCode.JAPANESE, description="Target language"
    )


class TranslationResponse(BaseModel):
    translated_text: str = Field(..., description="Translated text")
    src_lang: Optional[LanguageCode] = Field(
        None, description="Detected source language"
    )
