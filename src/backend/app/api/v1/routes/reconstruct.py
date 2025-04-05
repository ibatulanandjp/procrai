from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.reconstruction import (
    ReconstructionRequest,
    ReconstructionResponse,
)
from app.api.v1.services.reconstruction_service import ReconstructionService

router = APIRouter()


@router.post("/", summary="Reconstruct PDF with translated text")
async def reconstruct_document(
    request: ReconstructionRequest,
    reconstruction_service: ReconstructionService = Depends(ReconstructionService),
) -> ReconstructionResponse:
    """
    Reconstruct a PDF with translated text while maintaining the original layout.
    """
    try:
        output_filename = await reconstruction_service.reconstruct_pdf(
            elements=request.elements,
            original_filename=request.original_filename,
        )
        return ReconstructionResponse(
            filename=output_filename, message="PDF reconstructed successfully."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reconstructing PDF: {str(e)}"
        )
