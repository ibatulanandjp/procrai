from typing import List

from pydantic import BaseModel, Field

from app.api.v1.schemas.document import DocumentElement


class OcrResponse(BaseModel):
    elements: List[DocumentElement] = Field(
        ..., description="List of extracted elements"
    )
    page_count: int = Field(..., description="Number of pages in the document")
