import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import app_config
from app.core.logging import logger


def create_application() -> FastAPI:
    app = FastAPI(**app_config.fastapi_kwargs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=app_config.settings.API_V1_STR)
    logger.info("Application started")

    return app


app = create_application()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
