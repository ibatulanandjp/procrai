from typing import List

from pydantic import BaseModel, Field

from app.api.v1.schemas.document import DocumentElement


class ReconstructionRequest(BaseModel):
    elements: List[DocumentElement] = Field(
        ...,
        description="List of translated elements to reconstruct the document.",
    )
    original_filename: str = Field(
        ...,
        description="Original file name of the document being reconstructed.",
    )


class ReconstructionResponse(BaseModel):
    filename: str = Field(
        ...,
        description="The name of the reconstructed document.",
    )
    message: str = Field(
        ...,
        description="Message indicating the status of the reconstruction.",
    )
