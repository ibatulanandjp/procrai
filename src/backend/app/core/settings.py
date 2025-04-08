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

    # File settings
    MAX_FILE_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: list[str] = Field(
        default_factory=lambda: ["pdf", "png", "jpg", "jpeg"],
        title="Allowed file extensions",
    )
    UPLOAD_DIR: str = "uploads"

    # OCR settings
    OCR_ENGINE: str = "tesseract"
    OCR_LANGUAGE: str = "eng"

    # Translation settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"

    # Output settings
    OUTPUT_DIR: str = "outputs"

    # Font settings
    FONT_DIR: str = "fonts"

    @property
    def allowed_extensions(self) -> set[str]:
        return set(self.ALLOWED_EXTENSIONS)

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
