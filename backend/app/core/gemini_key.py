# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Resolución centralizada de la clave de API de Gemini.

Prioridad: valor guardado en `configuracion_sistema` (asistente/Configuración)
y, como respaldo, la variable de entorno `GEMINI_API_KEY` (desarrollo).
"""

import inspect
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ConfiguracionSistemaORM
from app.core.config import settings
from app.core.gemini_crypto import (
    decrypt_gemini_key,
    encrypt_gemini_key,
    is_encrypted_gemini_key,
)


async def resolver_gemini_key(db: AsyncSession) -> Optional[str]:
    """Devuelve la clave descifrada de BD; si no existe, usa la del entorno.

    Las claves antiguas en texto plano se migran al formato cifrado durante la
    primera lectura que tenga una sesión persistente disponible.
    """
    resultado = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = resultado.scalars().first()
    if config and config.gemini_api_key:
        if is_encrypted_gemini_key(config.gemini_api_key):
            return decrypt_gemini_key(config.gemini_api_key)

        # Compatibilidad de migración: no deja nuevas claves en texto plano.
        clave_plana = config.gemini_api_key
        config.gemini_api_key = encrypt_gemini_key(clave_plana)
        flush = getattr(db, "flush", None)
        if flush is not None:
            resultado_flush = flush()
            if inspect.isawaitable(resultado_flush):
                await resultado_flush
        return clave_plana
    return settings.GEMINI_API_KEY or None
