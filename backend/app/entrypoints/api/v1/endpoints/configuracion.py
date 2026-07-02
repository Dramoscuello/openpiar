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
        gemini_api_key=config.gemini_api_key,
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

    if body.gemini_api_key is not None:
        config.gemini_api_key = body.gemini_api_key or None

    if body.contexto_institucion is not None:
        config.contexto_institucion = body.contexto_institucion

    await db.flush()

    logger.info("Configuración del sistema actualizada por directivo.")

    return _build_response(config)
