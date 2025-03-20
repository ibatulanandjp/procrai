from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import app_config


def create_application() -> FastAPI:
    app = FastAPI(**app_config.fastapi_kwargs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_application()


@app.get("/")
async def root():
    return {"message": "Welcome to Procrai!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)