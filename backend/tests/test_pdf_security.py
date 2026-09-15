# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Pruebas del cifrado AES-256 de los PDF oficiales y del nombre aleatorio."""

import io
import re

import pytest
from pypdf import PdfReader
from pypdf.constants import UserAccessPermissions as UAP
from pypdf.errors import FileNotDecryptedError
from reportlab.pdfgen import canvas

from app.core.pdf_security import (
    nombre_archivo_piar,
    pdf_esta_cifrado,
    proteger_pdf,
)


def _pdf_simple(texto: str = "Contenido sensible del PIAR") -> bytes:
    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer)
    lienzo.drawString(72, 720, texto)
    lienzo.save()
    return buffer.getvalue()


def test_pdf_protegido_exige_password_y_abre_con_el_documento():
    original = _pdf_simple()
    assert pdf_esta_cifrado(original) is False

    protegido = proteger_pdf(original, "1234567890")
    assert protegido.startswith(b"%PDF")
    assert pdf_esta_cifrado(protegido) is True

    lector = PdfReader(io.BytesIO(protegido))
    assert lector.is_encrypted
    with pytest.raises(FileNotDecryptedError):
        lector.pages[0].extract_text()

    assert lector.decrypt("0000000000") == 0
    assert lector.decrypt("1234567890") in (1, 2)
    assert "Contenido sensible del PIAR" in lector.pages[0].extract_text()


def test_proteger_pdf_es_idempotente_y_no_cambia_la_password():
    protegido = proteger_pdf(_pdf_simple(), "ABC123")
    assert proteger_pdf(protegido, "ABC123") == protegido
    assert proteger_pdf(protegido, "OTRA-CLAVE") == protegido

    lector = PdfReader(io.BytesIO(proteger_pdf(protegido, "OTRA-CLAVE")))
    assert lector.decrypt("OTRA-CLAVE") == 0
    assert lector.decrypt("ABC123") == 1  # usuario, no owner: el owner se deriva de SECRET_KEY


def test_permisos_solo_impresion_y_accesibilidad():
    protegido = proteger_pdf(_pdf_simple(), "123456")
    lector = PdfReader(io.BytesIO(protegido))
    lector.decrypt("123456")
    permisos = lector.user_access_permissions

    assert UAP.PRINT in permisos
    assert UAP.EXTRACT_TEXT_AND_GRAPHICS in permisos  # lectores de pantalla
    for bloqueado in (UAP.MODIFY, UAP.EXTRACT, UAP.ADD_OR_MODIFY, UAP.FILL_FORM_FIELDS, UAP.ASSEMBLE_DOC):
        assert bloqueado not in permisos


def test_proteger_pdf_rechaza_password_vacia():
    with pytest.raises(ValueError):
        proteger_pdf(_pdf_simple(), "   ")


def test_nombre_archivo_piar_sanitiza_y_genera_codigo_aleatorio():
    nombre = nombre_archivo_piar("María José", "Pérez Gómez")
    assert re.fullmatch(r"PIAR_Maria_Jose_Perez_Gomez_[A-Z0-9]{6}\.pdf", nombre)

    otro = nombre_archivo_piar("María José", "Pérez Gómez")
    assert re.fullmatch(r"PIAR_Maria_Jose_Perez_Gomez_[A-Z0-9]{6}\.pdf", otro)
    assert nombre.split("_")[5] != otro.split("_")[5]


def test_nombre_archivo_piar_sin_datos_del_estudiante_no_falla():
    nombre = nombre_archivo_piar(None, "")
    assert re.fullmatch(r"PIAR_Estudiante_[A-Z0-9]{6}\.pdf", nombre)
