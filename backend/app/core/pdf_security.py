# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Protección de PDFs generados por OpenPiar.

Cifra los documentos con AES-256 (PyMuPDF) usando el número de documento del
estudiante como contraseña de apertura. El owner password se deriva de
SECRET_KEY para que las restricciones de permisos no puedan retirarse desde un
editor de PDF sin la clave del servidor.
"""

import hashlib
import hmac
import io
import re
import secrets
import string
import unicodedata
from typing import Optional

from app.core.config import settings

ALFABETO_CODIGO = string.ascii_uppercase + string.digits


def _owner_password() -> str:
    """Deriva un owner password estable a partir de SECRET_KEY (máx. 40 caracteres)."""
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        b"openpiar-pdf-owner",
        hashlib.sha256,
    ).hexdigest()
    return digest[:40]


def pdf_esta_cifrado(pdf_bytes: bytes) -> bool:
    """Indica si el PDF ya requiere contraseña para abrirse."""
    import fitz

    documento = fitz.open(stream=bytes(pdf_bytes), filetype="pdf")
    try:
        return bool(documento.needs_pass or documento.is_encrypted)
    finally:
        documento.close()


def proteger_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Cifra un PDF con AES-256. Es idempotente: si ya está cifrado lo deja igual.

    Permisos: solo impresión y accesibilidad (sin copiar, modificar, anotar ni
    ensamblar). La apertura siempre exige `password`.
    """
    password = (password or "").strip()
    if not password:
        raise ValueError("La contraseña del PDF no puede estar vacía.")
    pdf_bytes = bytes(pdf_bytes)
    if pdf_esta_cifrado(pdf_bytes):
        return pdf_bytes

    import fitz

    documento = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        salida = io.BytesIO()
        permisos = (
            fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_PRINT_HQ
            | fitz.PDF_PERM_ACCESSIBILITY
        )
        documento.save(
            salida,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=_owner_password(),
            permissions=permisos,
        )
        return salida.getvalue()
    finally:
        documento.close()


def _sanitizar_nombre(valor: Optional[str]) -> str:
    """Normaliza un nombre para usarlo en un archivo: sin acentos ni símbolos."""
    if not valor:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(valor))
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = re.sub(r"[^A-Za-z0-9]+", "_", sin_acentos).strip("_")
    return re.sub(r"_+", "_", limpio)


def nombre_archivo_piar(nombres: Optional[str], apellidos: Optional[str]) -> str:
    """Construye PIAR_<Nombre_Apellido>_<código6>.pdf sin datos sensibles.

    El código alfanumérico se genera en cada llamada para que cada descarga
    entregue un nombre distinto.
    """
    partes = [_sanitizar_nombre(nombres), _sanitizar_nombre(apellidos)]
    nombre = "_".join(parte for parte in partes if parte) or "Estudiante"
    codigo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))
    return f"PIAR_{nombre}_{codigo}.pdf"
