from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    ALLOWED_EXTENSIONS: list[str] = Field(
        default_factory=lambda: ["pdf", "png", "jpg", "jpeg"],
        title="Allowed file extensions",
    )
    UPLOAD_DIR: str = "uploads"

    @property
    def allowed_extensions(self) -> list[str]:
        return set(self.ALLOWED_EXTENSIONS)

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
print(settings.allowed_extensions)
