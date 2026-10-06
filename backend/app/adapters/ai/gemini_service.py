# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Servicio único para llamadas controladas a Google Gemini."""

import asyncio
import json
import logging
import time
from typing import Any, Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.gemini_crypto import GeminiCryptoError
from app.core.gemini_key import resolver_gemini_key

logger = logging.getLogger(__name__)


class GeminiServiceError(RuntimeError):
    """Error seguro de comunicación o configuración de Gemini."""


class GeminiQuotaError(GeminiServiceError):
    """Gemini rechazó la solicitud por cuota o rate limit."""


class GeminiTimeoutError(GeminiServiceError):
    """Gemini no respondió dentro del tiempo permitido."""


class GeminiConfigurationError(GeminiServiceError):
    """La IA está deshabilitada o no tiene una clave configurada."""


def _es_error_de_cuota(exc: Exception) -> bool:
    texto = f"{type(exc).__name__} {exc}".lower()
    return any(
        indicador in texto
        for indicador in ("429", "quota", "rate limit", "resource_exhausted")
    )


class GeminiService:
    """Encapsula clave, modelo, timeout, salida estructurada y errores seguros."""

    def __init__(
        self,
        db,
        *,
        usuario_id: Optional[Any] = None,
        piar_id: Optional[Any] = None,
    ) -> None:
        self._db = db
        self._usuario_id = usuario_id
        self._piar_id = piar_id
        self._settings = get_settings()

    async def _generate(
        self,
        prompt: str,
        *,
        response_schema: Optional[dict] = None,
    ) -> str:
        if not self._settings.AI_EXTERNAL_ENABLED:
            raise GeminiConfigurationError("La IA externa está deshabilitada.")

        try:
            api_key = await resolver_gemini_key(self._db)
        except GeminiCryptoError as exc:
            logger.warning(
                "Gemini cifrado inválido usuario_id=%s piar_id=%s",
                self._usuario_id,
                self._piar_id,
            )
            raise GeminiConfigurationError(str(exc)) from exc
        except Exception as exc:
            logger.warning(
                "Gemini configuración inválida usuario_id=%s piar_id=%s tipo=%s",
                self._usuario_id,
                self._piar_id,
                type(exc).__name__,
            )
            raise GeminiConfigurationError(
                "No se pudo leer la configuración de Gemini. Revisa los logs del servidor."
            ) from exc
        if not api_key:
            raise GeminiConfigurationError(
                "No hay una clave de Gemini configurada. "
                "Cárgala en Gestión Escolar → Configuración."
            )

        config = types.GenerateContentConfig(
            response_mime_type="application/json" if response_schema else None,
            response_json_schema=response_schema,
            temperature=0.4,
            max_output_tokens=self._settings.GEMINI_MAX_OUTPUT_TOKENS,
        )
        started = time.monotonic()
        try:
            client = genai.Client(api_key=api_key)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=self._settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config,
                ),
                timeout=self._settings.GEMINI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            logger.warning(
                "Gemini timeout usuario_id=%s piar_id=%s modelo=%s",
                self._usuario_id,
                self._piar_id,
                self._settings.GEMINI_MODEL,
            )
            raise GeminiTimeoutError("Gemini agotó el tiempo de respuesta.") from exc
        except Exception as exc:
            if _es_error_de_cuota(exc):
                logger.warning(
                    "Gemini cuota agotada usuario_id=%s piar_id=%s modelo=%s",
                    self._usuario_id,
                    self._piar_id,
                    self._settings.GEMINI_MODEL,
                )
                raise GeminiQuotaError("La cuota de Gemini está agotada.") from exc
            logger.warning(
                "Gemini error usuario_id=%s piar_id=%s modelo=%s tipo=%s",
                self._usuario_id,
                self._piar_id,
                self._settings.GEMINI_MODEL,
                type(exc).__name__,
            )
            raise GeminiServiceError("No fue posible consultar el servicio de IA.") from exc

        texto = getattr(response, "text", None)
        if not texto:
            raise GeminiServiceError("Gemini devolvió una respuesta vacía.")
        logger.info(
            "Gemini solicitud completada usuario_id=%s piar_id=%s modelo=%s duracion_ms=%d",
            self._usuario_id,
            self._piar_id,
            self._settings.GEMINI_MODEL,
            int((time.monotonic() - started) * 1000),
        )
        return texto.strip()

    async def generate_text(self, prompt: str) -> str:
        return await self._generate(prompt)

    async def generate_json(self, prompt: str, schema: dict) -> dict:
        texto = await self._generate(prompt, response_schema=schema)
        try:
            resultado = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise GeminiServiceError("Gemini devolvió un formato inválido.") from exc
        if not isinstance(resultado, dict):
            raise GeminiServiceError("Gemini devolvió una estructura inválida.")
        return resultado
