# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Cifrado autenticado de claves de API de Gemini almacenadas en PostgreSQL."""

import base64
import binascii
import logging
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PREFIX = "enc:v1:"
_AAD = b"openpiar:gemini-api-key:v1"
_NONCE_BYTES = 12
_KEY_BYTES = 32
_FALLBACK_INFO = b"openpiar:gemini-key:v1"


class GeminiCryptoError(RuntimeError):
    """No se pudo cifrar o descifrar la clave de Gemini."""


def _encryption_key() -> bytes:
    """Clave de cifrado: GEMINI_ENCRYPTION_KEY o derivación de SECRET_KEY."""
    raw = get_settings().GEMINI_ENCRYPTION_KEY.strip()
    if raw:
        try:
            key = bytes.fromhex(raw) if len(raw) == 64 else base64.urlsafe_b64decode(
                raw + "=" * (-len(raw) % 4)
            )
        except (ValueError, binascii.Error) as exc:
            raise GeminiCryptoError(
                "GEMINI_ENCRYPTION_KEY debe ser hexadecimal de 64 caracteres o Base64 URL-safe."
            ) from exc

        if len(key) != _KEY_BYTES:
            raise GeminiCryptoError(
                "GEMINI_ENCRYPTION_KEY debe representar exactamente 32 bytes."
            )
        return key

    # Fallback documentado: sin variable explícita, se deriva de SECRET_KEY para
    # no guardar la clave de Gemini en texto plano. Definir GEMINI_ENCRYPTION_KEY
    # separa ambos secretos y permite rotarla de forma independiente.
    logger.warning(
        "GEMINI_ENCRYPTION_KEY no configurada: se deriva la clave de cifrado "
        "desde SECRET_KEY. Define GEMINI_ENCRYPTION_KEY en el entorno."
    )
    return HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=None,
        info=_FALLBACK_INFO,
    ).derive(get_settings().SECRET_KEY.encode("utf-8"))


def is_encrypted_gemini_key(value: str | None) -> bool:
    return bool(value and value.startswith(PREFIX))


def encrypt_gemini_key(value: str) -> str:
    plaintext = value.strip()
    if not plaintext:
        raise ValueError("La clave de Gemini no puede estar vacía.")

    nonce = secrets.token_bytes(_NONCE_BYTES)
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce,
        plaintext.encode("utf-8"),
        _AAD,
    )
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{PREFIX}{payload}"


def decrypt_gemini_key(value: str) -> str:
    if not is_encrypted_gemini_key(value):
        raise ValueError("La clave de Gemini no tiene un formato cifrado válido.")

    try:
        payload = base64.urlsafe_b64decode(value[len(PREFIX):])
        nonce = payload[:_NONCE_BYTES]
        ciphertext = payload[_NONCE_BYTES:]
        return AESGCM(_encryption_key()).decrypt(nonce, ciphertext, _AAD).decode("utf-8")
    except (ValueError, binascii.Error, InvalidTag) as exc:
        raise GeminiCryptoError(
            "No se pudo descifrar la clave de Gemini almacenada. "
            "Verifica que GEMINI_ENCRYPTION_KEY (o SECRET_KEY) no haya cambiado."
        ) from exc
