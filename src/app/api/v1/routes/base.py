from fastapi import APIRouter

from app.core.logging import logger

router = APIRouter()
logger.info("API v1 router initialized")


@router.get("/", summary="Welcome to Procrai!")
async def root():
    return {"message": "Welcome to Procrai!"}


@router.get("/health", summary="Check if the server is running")
async def health():
    return {"status": "ok"}
