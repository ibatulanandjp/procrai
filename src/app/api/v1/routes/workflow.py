import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.v1.services.workflow_service import WorkflowService
from app.core.config import app_config
from app.core.logging import logger

router = APIRouter()

UPLOAD_DIR = app_config.settings.UPLOAD_DIR


@router.post("/process", summary="Process a document through the workflow")
async def process_document(
    file: UploadFile = File(...),
    src_lang: str = "ja",
    target_lang: str = "en",
    workflow_service: WorkflowService = Depends(WorkflowService),
) -> FileResponse:
    """
    Process a document through the complete workflow:
    OCR -> Translate -> Reconstruct -> Download
    Returns the final PDF file.

    Args:
        file: The file to upload
        src_lang: Source language for translation
        target_lang: Target language for translation
        workflow_service: Workflow service dependency
    Returns:
        FileResponse: Response containing the final PDF file
    Raises:
        HTTPException: If the file upload or processing fails
    Raises:
        Exception: If any unexpected error occurs
    """
    try:
        logger.info(f"Uploading file: {file.filename}")
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        # Process the workflow
        output_filepath = await workflow_service.process_workflow(
            filename=file.filename, src_lang=src_lang, target_lang=target_lang
        )

        # Return the final PDF file
        output_path = os.path.join(app_config.settings.OUTPUT_DIR, output_filepath)
        return FileResponse(
            output_path, media_type="application/pdf", filename=output_filepath
        )

    except Exception as e:
        logger.error(f"Error during workflow processing: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error during workflow processing: {str(e)}"
        )
