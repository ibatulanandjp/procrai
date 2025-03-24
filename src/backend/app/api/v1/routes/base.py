from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Welcome to Procrai!")
async def root():
    return {"message": "Welcome to Procrai!"}


@router.get("/health", summary="Check if the server is running")
async def health():
    return {"status": "ok"}
