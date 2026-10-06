# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Resolución de la clave de Gemini: prioridad base de datos > entorno."""

import logging
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core import gemini_key as modulo
from app.core.gemini_crypto import (
    GeminiCryptoError,
    decrypt_gemini_key,
    encrypt_gemini_key,
)
from app.core.gemini_key import resolver_gemini_key
from app.entrypoints.api.v1.endpoints.configuracion import _build_response
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
    monkeypatch.setattr(modulo.settings, "GEMINI_ENCRYPTION_KEY", "11" * 32)
    config = NS(gemini_api_key="clave-bd")
    llave = await resolver_gemini_key(_db_con(config))
    assert llave == "clave-bd"
    assert config.gemini_api_key.startswith("enc:v1:")


@pytest.mark.asyncio
async def test_usa_el_entorno_si_la_bd_no_tiene_clave(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_API_KEY", "clave-entorno")
    assert await resolver_gemini_key(_db_con(NS(gemini_api_key=None))) == "clave-entorno"
    assert await resolver_gemini_key(_db_con(None)) == "clave-entorno"


@pytest.mark.asyncio
async def test_descifra_la_clave_cifrada(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_ENCRYPTION_KEY", "22" * 32)
    config = NS(gemini_api_key=encrypt_gemini_key("clave-cifrada"))

    assert await resolver_gemini_key(_db_con(config)) == "clave-cifrada"


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


def test_cifrado_gemini_no_guarda_la_clave_en_claro(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_ENCRYPTION_KEY", "33" * 32)

    cifrada = encrypt_gemini_key("AIza-secret-value")

    assert cifrada.startswith("enc:v1:")
    assert "AIza-secret-value" not in cifrada
    assert decrypt_gemini_key(cifrada) == "AIza-secret-value"


def test_cifrado_sin_variable_deriva_de_secret_key(monkeypatch, caplog):
    monkeypatch.setattr(modulo.settings, "GEMINI_ENCRYPTION_KEY", "")
    monkeypatch.setattr(modulo.settings, "SECRET_KEY", "secreto-de-prueba")

    with caplog.at_level(logging.WARNING, logger="app.core.gemini_crypto"):
        cifrada = encrypt_gemini_key("AIza-clave")

    assert cifrada.startswith("enc:v1:")
    assert decrypt_gemini_key(cifrada) == "AIza-clave"
    assert "GEMINI_ENCRYPTION_KEY no configurada" in caplog.text


def test_encryption_key_invalida_falla_con_mensaje_claro(monkeypatch):
    monkeypatch.setattr(modulo.settings, "GEMINI_ENCRYPTION_KEY", "no-es-clave")

    with pytest.raises(GeminiCryptoError) as error:
        encrypt_gemini_key("AIza-clave")

    assert "32 bytes" in str(error.value)


def test_respuesta_de_configuracion_no_expone_la_clave():
    response = _build_response(NS(
        nombre_institucion="Colegio",
        nit="123456789-0",
        codigo_dane="123456789012",
        direccion="Calle 1",
        telefono_contacto=None,
        correo_contacto=None,
        nombre_rector=None,
        gemini_api_key="enc:v1:secreto",
        contexto_institucion=None,
        pei_modelo_pedagogico=None,
    ))

    assert response.tiene_gemini_key is True
    assert "gemini_api_key" not in response.model_dump()
