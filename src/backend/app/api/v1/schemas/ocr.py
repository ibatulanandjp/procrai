from pydantic import BaseModel, Field


class OcrResponse(BaseModel):
    extracted_text: str = Field(..., description="Extracted text")
