from enum import Enum

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    HEADING = "heading"
    FOOTER = "footer"


class Position(BaseModel):
    x0: float = Field(..., description="X coordinate of the top-left corner")
    y0: float = Field(..., description="Y coordinate of the top-left corner")
    x1: float = Field(..., description="X coordinate of the bottom-right corner")
    y1: float = Field(..., description="Y coordinate of the bottom-right corner")
    page: int = Field(..., description="Page number")


class OcrElement(BaseModel):
    type: ElementType = Field(..., description="Type of the element")
    content: str = Field(..., description="Content of the element")
    position: Position = Field(..., description="Position of the element")
    confidence: float = Field(..., description="OCR confidence score")
    metadata: dict = Field({}, description="Additional element metadata")


class OcrResponse(BaseModel):
    elements: list[OcrElement] = Field(..., description="List of extracted elements")
    page_count: int = Field(..., description="Number of pages in the document")
