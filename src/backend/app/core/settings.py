from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Procrai"
    DEBUG: bool = False

    # API settings
    API_V1_STR: str = "/api/v1"

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # OCR settings
    OCR_ENGINE: str = "tesseract"
    OCR_LANGUAGE: str = "eng"

    # File settings
    MAX_FILE_SIZE: int = 10485760
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
