from fastapi import APIRouter

from .routes import (
    base,
    download,
    ocr,
    reconstruct,
    translate,
    upload,
    workflow,
)

api_router = APIRouter()

api_router.include_router(base.router, tags=["base"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(translate.router, prefix="/translate", tags=["translate"])
api_router.include_router(
    reconstruct.router, prefix="/reconstruct", tags=["reconstruct"]
)
api_router.include_router(download.router, prefix="/download", tags=["download"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
