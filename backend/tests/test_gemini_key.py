# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Resolución de la clave de Gemini: prioridad base de datos > entorno."""

from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core import gemini_key as modulo
from app.core.gemini_key import resolver_gemini_key
from app.entrypoints.api.v1.endpoints import piars


def _db_con(config):
    resultado = MagicMock()
    resultado.scalars.return_value.first.return_value = config
    db = MagicMock()
    db.execute = AsyncMock(return_value=resultado)
    return db


@pytest.mark.asyncio
async def test_prioriza_la_clave_guardada_en_la_bd(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_API_KEY", "clave-entorno")
    llave = await resolver_gemini_key(_db_con(NS(gemini_api_key="clave-bd")))
    assert llave == "clave-bd"


@pytest.mark.asyncio
async def test_usa_el_entorno_si_la_bd_no_tiene_clave(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_API_KEY", "clave-entorno")
    assert await resolver_gemini_key(_db_con(NS(gemini_api_key=None))) == "clave-entorno"
    assert await resolver_gemini_key(_db_con(None)) == "clave-entorno"


@pytest.mark.asyncio
async def test_devuelve_none_sin_bd_ni_entorno(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_API_KEY", "")
    assert await resolver_gemini_key(_db_con(None)) is None


@pytest.mark.asyncio
async def test_get_gemini_key_lanza_400_sin_clave(monkeypatch):
    monkeypatch.setattr(modulo, "resolver_gemini_key", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as error:
        await piars.get_gemini_key(_db_con(None))
    assert error.value.status_code == 400
