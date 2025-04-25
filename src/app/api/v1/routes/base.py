from fastapi import APIRouter

from app.core.logging import logger

router = APIRouter()
logger.info("API v1 router initialized")


@router.get("/", summary="Welcome to Procrai!")
async def root():
    """
    Welcome message for the API.
    Returns:
        dict: A welcome message
    """
    return {"message": "Welcome to Procrai!"}


@router.get("/health", summary="Check if the server is running")
async def health():
    """
    Health check endpoint.
    Returns:
        dict: A health status message
    """
    logger.info("Health check: Server is running")
    return {"status": "ok"}
