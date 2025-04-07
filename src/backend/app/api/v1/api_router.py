from fastapi import APIRouter

from app.api.v1.routes import base, download, ocr, reconstruct, translate, upload

api_router = APIRouter()
api_router.include_router(base.router, tags=["base"])
api_router.include_router(upload.router, tags=["upload"], prefix="/upload")
api_router.include_router(ocr.router, tags=["ocr"], prefix="/ocr")
api_router.include_router(translate.router, tags=["translate"], prefix="/translate")
api_router.include_router(
    reconstruct.router, tags=["reconstruct"], prefix="/reconstruct"
)
api_router.include_router(download.router, prefix="/download", tags=["download"])
