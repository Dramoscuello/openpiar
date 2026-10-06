# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Pruebas del servicio centralizado de Gemini."""

from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

from app.adapters.ai import gemini_service
from app.adapters.ai.gemini_service import (
    GeminiConfigurationError,
    GeminiService,
)
from app.core.gemini_crypto import GeminiCryptoError


@pytest.mark.asyncio
async def test_servicio_gemini_envia_prompt_y_devuelve_texto(monkeypatch):
    monkeypatch.setattr(
        gemini_service,
        "resolver_gemini_key",
        lambda _db: _async_value("clave-de-prueba"),
    )
    settings = gemini_service.get_settings()
    monkeypatch.setattr(settings, "AI_EXTERNAL_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_ENCRYPTION_KEY", "44" * 32)

    respuesta = NS(text="respuesta segura")
    cliente = MagicMock()
    cliente.models.generate_content.return_value = respuesta
    monkeypatch.setattr(gemini_service.genai, "Client", lambda api_key: cliente)

    resultado = await GeminiService(NS(), usuario_id="u", piar_id="p").generate_text(
        "Prompt sin identificadores"
    )

    assert resultado == "respuesta segura"
    cliente.models.generate_content.assert_called_once()
    assert cliente.models.generate_content.call_args.kwargs["contents"] == "Prompt sin identificadores"


@pytest.mark.asyncio
async def test_servicio_gemini_rechaza_ia_deshabilitada(monkeypatch):
    settings = gemini_service.get_settings()
    monkeypatch.setattr(settings, "AI_EXTERNAL_ENABLED", False)

    with pytest.raises(GeminiConfigurationError):
        await GeminiService(NS()).generate_text("prompt")


@pytest.mark.asyncio
async def test_servicio_gemini_reporta_error_de_cifrado(monkeypatch):
    async def _raise(_db):
        raise GeminiCryptoError("No se pudo descifrar la clave de Gemini almacenada.")

    monkeypatch.setattr(gemini_service, "resolver_gemini_key", _raise)
    settings = gemini_service.get_settings()
    monkeypatch.setattr(settings, "AI_EXTERNAL_ENABLED", True)

    with pytest.raises(GeminiConfigurationError) as error:
        await GeminiService(NS()).generate_text("prompt")

    assert "descifrar" in str(error.value)


@pytest.mark.asyncio
async def test_servicio_gemini_sin_clave_indica_donde_configurarla(monkeypatch):
    monkeypatch.setattr(
        gemini_service, "resolver_gemini_key", lambda _db: _async_value(None)
    )
    settings = gemini_service.get_settings()
    monkeypatch.setattr(settings, "AI_EXTERNAL_ENABLED", True)

    with pytest.raises(GeminiConfigurationError) as error:
        await GeminiService(NS()).generate_text("prompt")

    assert "Configuración" in str(error.value)


async def _async_value(value):
    return value
