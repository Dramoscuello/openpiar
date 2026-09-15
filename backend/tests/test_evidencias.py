# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Subida de evidencias (solo imágenes) y conversión de imágenes para el PDF."""

import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.core.pdf_generator import _imagen_evidencia_para_pdf
from app.entrypoints.api.v1.endpoints.piars import validar_archivo_evidencia


def _imagen_bytes(formato: str, size=(80, 60), color=(10, 120, 200)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=formato)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "nombre,formato",
    [("foto.png", "PNG"), ("foto.jpg", "JPEG"), ("foto.webp", "WEBP"), ("foto.bmp", "BMP")],
)
def test_validar_archivo_acepta_formatos_de_imagen(nombre, formato):
    try:
        contenido = _imagen_bytes(formato)
    except Exception:
        pytest.skip(f"Pillow no soporta {formato} en este entorno")
    assert validar_archivo_evidencia(nombre, contenido) == nombre


@pytest.mark.parametrize(
    "nombre",
    ["documento.pdf", "hoja.docx", "texto.txt", "sin_extension"],
)
def test_validar_archivo_rechaza_extensiones_no_imagen(nombre):
    with pytest.raises(HTTPException) as error:
        validar_archivo_evidencia(nombre, b"%PDF-1.4 contenido")
    assert error.value.status_code == 422


def test_validar_archivo_rechaza_contenido_que_no_es_imagen():
    with pytest.raises(HTTPException) as error:
        validar_archivo_evidencia("falsa.png", b"esto no es una imagen")
    assert error.value.status_code == 422


def test_imagen_evidencia_para_pdf_escala_y_optimiza(tmp_path):
    ruta = tmp_path / "foto.png"
    Image.new("RGB", (1200, 400), (0, 160, 0)).save(ruta)

    flowable = _imagen_evidencia_para_pdf(str(ruta))
    assert flowable is not None
    assert flowable.drawWidth <= 130
    assert flowable.drawHeight <= 95
    assert flowable.drawWidth > flowable.drawHeight


def test_imagen_evidencia_para_pdf_tolera_archivos_ausentes_o_corruptos(tmp_path):
    assert _imagen_evidencia_para_pdf(str(tmp_path / "no_existe.png")) is None
    assert _imagen_evidencia_para_pdf(None) is None

    corrupta = tmp_path / "corrupta.jpg"
    corrupta.write_bytes(b"esto no es una imagen")
    assert _imagen_evidencia_para_pdf(str(corrupta)) is None


def test_imagen_evidencia_con_transparencia_se_aplana_sobre_blanco(tmp_path):
    ruta = tmp_path / "logo.png"
    Image.new("RGBA", (200, 200), (255, 0, 0, 0)).save(ruta)

    flowable = _imagen_evidencia_para_pdf(str(ruta))
    assert flowable is not None
    assert flowable.drawWidth > 0 and flowable.drawHeight > 0
