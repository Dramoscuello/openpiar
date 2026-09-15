# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Resolución centralizada de la clave de API de Gemini.

Prioridad: valor guardado en `configuracion_sistema` (asistente/Configuración)
y, como respaldo, la variable de entorno `GEMINI_API_KEY` (desarrollo).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ConfiguracionSistemaORM
from app.core.config import settings


async def resolver_gemini_key(db: AsyncSession) -> Optional[str]:
    """Devuelve la clave de Gemini configurada en la BD; si no existe, la del entorno."""
    resultado = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = resultado.scalars().first()
    if config and config.gemini_api_key:
        return config.gemini_api_key
    return settings.GEMINI_API_KEY or None
