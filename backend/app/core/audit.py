# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Auditoría de accesos a información sensible mediante logs estructurados.

Decisión de producto: no se persiste en base de datos; se emite una línea de
log con identificadores y metadatos del request, sin contenido clínico ni
secretos.
"""

import logging
from typing import Optional

from fastapi import Request

logger = logging.getLogger("app.audit")

_MAX_CAMPO = 200


def _limpiar(valor: Optional[str]) -> Optional[str]:
    """Quita caracteres de control y limita la longitud para el log."""
    if not valor:
        return None
    limpio = "".join(caracter for caracter in valor if caracter.isprintable())
    return limpio[:_MAX_CAMPO]


def _ip_cliente(request: Request) -> Optional[str]:
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else None


def registrar_acceso_sensible(
    request: Request,
    *,
    usuario_id,
    estudiante_id,
    recurso: str,
    accion: str,
) -> None:
    """Registra un acceso a información sensible (salud, familia, etc.)."""
    logger.info(
        "acceso_sensible recurso=%s accion=%s usuario_id=%s estudiante_id=%s ip=%s user_agent=%s",
        recurso,
        accion,
        usuario_id,
        estudiante_id,
        _ip_cliente(request),
        _limpiar(request.headers.get("user-agent")),
    )
