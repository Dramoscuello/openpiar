# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de configuración del sistema.

Permite al directivo consultar y actualizar la configuración
post-setup (contexto institucional, API key de Gemini, etc.).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ConfiguracionSistemaORM
from app.adapters.db.session import get_db
from app.core.gemini_crypto import encrypt_gemini_key
from app.entrypoints.api.dependencies import DirectivoUser
from app.entrypoints.api.schemas import (
    ActualizarConfiguracionRequest,
    ConfiguracionSistemaResponse,
)

router = APIRouter(prefix="/configuracion", tags=["Configuración del Sistema"])
logger = logging.getLogger(__name__)


def _build_response(config: ConfiguracionSistemaORM) -> ConfiguracionSistemaResponse:
    return ConfiguracionSistemaResponse(
        nombre_institucion=config.nombre_institucion,
        nit=config.nit,
        codigo_dane=config.codigo_dane,
        direccion=config.direccion,
        telefono_contacto=config.telefono_contacto,
        correo_contacto=config.correo_contacto,
        nombre_rector=config.nombre_rector,
        tiene_gemini_key=bool(config.gemini_api_key),
        contexto_institucion=config.contexto_institucion,
        pei_modelo_pedagogico=config.pei_modelo_pedagogico,
    )


@router.get(
    "",
    response_model=ConfiguracionSistemaResponse,
    summary="Consultar configuración del sistema",
    description="Retorna los datos de configuración institucional. Solo directivos.",
)
async def get_configuracion(
    _directivo: DirectivoUser,
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionSistemaResponse:
    result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = result.scalars().first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración del sistema no encontrada.",
        )

    return _build_response(config)


@router.patch(
    "",
    response_model=ConfiguracionSistemaResponse,
    summary="Actualizar configuración del sistema",
    description=(
        "Permite al directivo actualizar el contexto institucional y la API key "
        "de Gemini después del setup inicial."
    ),
)
async def update_configuracion(
    body: ActualizarConfiguracionRequest,
    _directivo: DirectivoUser,
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionSistemaResponse:
    result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = result.scalars().first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración del sistema no encontrada.",
        )

    cambios = body.model_dump(exclude_unset=True)
    if "gemini_api_key" in cambios:
        api_key = cambios["gemini_api_key"]
        try:
            config.gemini_api_key = (
                encrypt_gemini_key(api_key) if api_key and api_key.strip() else None
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo proteger la configuración de IA.",
            ) from exc

    if "contexto_institucion" in cambios:
        config.contexto_institucion = cambios["contexto_institucion"]

    await db.flush()

    logger.info("Configuración del sistema actualizada por directivo.")

    return _build_response(config)
