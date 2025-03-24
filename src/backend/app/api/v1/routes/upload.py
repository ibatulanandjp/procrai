import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import app_config

from ..helpers.file_helpers import is_file_type_allowed

router = APIRouter()

UPLOAD_DIR = app_config.settings.UPLOAD_DIR
ALLOWED_EXTENSIONS = app_config.settings.allowed_extensions
MAX_FILE_SIZE = app_config.settings.MAX_FILE_SIZE

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", summary="Upload a file")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:

    # Validate file type
    if not is_file_type_allowed(file, ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="File type not allowed",
        )

    # Validate file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size too large",
        )

    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return JSONResponse(content={"filename": file.filename, "message": "File uploaded"})
