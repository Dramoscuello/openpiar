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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Sesión deslizante: expira tras 24 h sin actividad.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    # Reuso de un refresh recién rotado (carrera entre pestañas) sin revocar familia.
    REFRESH_REUSE_GRACE_SECONDS: int = 60
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "openpiar"
    JWT_AUDIENCE: str = "openpiar-web"

    # Cookies de sesión (refresh token HttpOnly)
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "strict"
    COOKIE_DOMAIN: str = ""

    # Token obligatorio para ejecutar el Setup Wizard en instalaciones nuevas.
    # Generar con: openssl rand -hex 32
    BOOTSTRAP_TOKEN: str = ""

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
    GEMINI_ENCRYPTION_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 30.0
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048
    AI_EXTERNAL_ENABLED: bool = True
    AI_INCLUDE_MEDICAL_DIAGNOSIS: bool = True


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton cacheado de la configuración.
    Usar como dependencia FastAPI: settings = Depends(get_settings)
    """
    return Settings()


# Instancia global para módulos que no usan DI (ej: Alembic env.py)
settings = get_settings()
