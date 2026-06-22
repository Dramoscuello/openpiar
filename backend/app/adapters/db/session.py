# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Sesión asíncrona de base de datos con SQLAlchemy 2.0.

Este módulo vive en la capa de adaptadores — NO en el dominio.
El dominio nunca importa desde aquí.
"""

from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Motor async — pool de conexiones PostgreSQL
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),  # Logea SQL solo en dev
    future=True,
    pool_pre_ping=True,       # Detecta conexiones muertas antes de usarlas
    pool_size=10,
    max_overflow=20,
)

# Factory de sesiones async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Evita lazy loads post-commit
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Base declarativa compartida por todos los modelos ORM
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base para todos los modelos SQLAlchemy de OpenPiar."""
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


# ---------------------------------------------------------------------------
# Dependencia FastAPI — inyecta la sesión en los endpoints
# ---------------------------------------------------------------------------

async def get_db() -> AsyncSession:  # type: ignore[return]
    """
    Dependency para FastAPI. Gestiona automáticamente:
    - Commit al finalizar sin error
    - Rollback ante cualquier excepción
    - Cierre de sesión siempre

    Uso:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
