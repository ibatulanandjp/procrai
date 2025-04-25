from typing import Any, Dict, List
from .settings import settings


class AppConfig:
    def __init__(self):
        self.settings = settings

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        return {
            "title": self.settings.APP_NAME,
            "openapi_url": f"{self.settings.API_V1_STR}/openapi.json",
            "docs_url": f"{self.settings.API_V1_STR}/docs",
            "redoc_url": f"{self.settings.API_V1_STR}/redoc",
        }

    @property
    def cors_origins(self) -> List[str]:
        return self.settings.BACKEND_CORS_ORIGINS


app_config = AppConfig()
