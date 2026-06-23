# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Configuración central de la aplicación OpenPiar.
Usa pydantic-settings para leer variables de entorno desde .env
y construir la URL de conexión a PostgreSQL dinámicamente.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación leída desde variables de entorno / .env.
    Todos los campos tienen valores por defecto seguros para desarrollo.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Aplicación
    # ------------------------------------------------------------------
    APP_ENV: str = "development"
    SHOW_DOCS: bool = True
    API_V1_STR: str = "/api/v1"

    # ------------------------------------------------------------------
    # Seguridad — JWT
    # ------------------------------------------------------------------
    SECRET_KEY: str = "dev-secret-key-change-in-production-please"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    ALGORITHM: str = "HS256"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte la cadena CSV de orígenes en lista."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ------------------------------------------------------------------
    # Base de datos (PostgreSQL)
    # ------------------------------------------------------------------
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "openpiar_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "openpiar_db"

    # URL directa (opcional: sobreescribe los campos individuales)
    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """
        Si DATABASE_URL está vacío, lo construye desde los campos individuales.
        Usa asyncpg como driver async para SQLAlchemy 2.0.
        """
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    # ------------------------------------------------------------------
    # Gemini API
    # ------------------------------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton cacheado de la configuración.
    Usar como dependencia FastAPI: settings = Depends(get_settings)
    """
    return Settings()


# Instancia global para módulos que no usan DI (ej: Alembic env.py)
settings = get_settings()
