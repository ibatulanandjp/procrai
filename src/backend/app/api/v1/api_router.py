from fastapi import APIRouter

from app.api.v1.routes import base, upload

api_router = APIRouter()
api_router.include_router(base.router, tags=["base"])
api_router.include_router(upload.router, tags=["upload"], prefix="/upload")
