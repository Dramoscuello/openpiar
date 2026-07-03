# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Middleware de guard de Setup.

Si el setup NO está completado, bloquea todas las rutas
excepto: /api/v1/setup/*, /api/v1/health, /docs, /openapi.json, /redoc.

Retorna 412 Precondition Failed con un mensaje claro.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.adapters.db.models import ConfiguracionSistemaORM
from app.adapters.db.session import AsyncSessionLocal

# Rutas que siempre están disponibles aunque el setup no esté completo
RUTAS_PUBLICAS = {
    "/api/v1/setup/status",
    "/api/v1/setup/test-db",
    "/api/v1/setup/configure",
    "/api/v1/setup/upload-pei",
    "/api/v1/familia",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}


async def setup_guard_middleware(request: Request, call_next):
    """
    Middleware que verifica si el setup fue completado.
    Solo aplica a rutas de la API (excluyendo las rutas públicas del setup).
    """
    path = request.url.path

    # Permitir rutas del setup y recursos estáticos
    if any(path.startswith(ruta) or path == ruta for ruta in RUTAS_PUBLICAS):
        return await call_next(request)

    # Solo verificar rutas de la API
    if not path.startswith("/api/"):
        return await call_next(request)

    # Consultar estado del setup en BD
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConfiguracionSistemaORM)
                .where(ConfiguracionSistemaORM.setup_completado == True)  # noqa: E712
                .limit(1)
            )
            completado = result.scalars().first() is not None
    except Exception:
        # Si la BD no está disponible, dejar pasar (el endpoint manejará el error)
        return await call_next(request)

    if not completado:
        return JSONResponse(
            status_code=412,
            content={
                "detail": (
                    "OpenPiar no está configurado. "
                    "Por favor completa el asistente de configuración inicial "
                    "en GET /api/v1/setup/status"
                ),
                "setup_required": True,
            },
        )

    return await call_next(request)
