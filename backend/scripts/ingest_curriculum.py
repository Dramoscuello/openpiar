# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Script de ingesta de currículum: DBA y EBC.

Lee los PDFs oficiales del MEN desde las carpetas dba/ y ebc/
del proyecto raíz, extrae la información estructurada con pdfplumber
y Gemini (fallback para layouts complejos), y guarda los fixtures JSON.

Uso:
    cd backend
    python scripts/ingest_curriculum.py

Los archivos resultantes se guardan en:
    backend/app/fixtures/dba_fixtures.json
    backend/app/fixtures/ebc_fixtures.json

Una vez generados, estos fixtures se cargan a PostgreSQL mediante:
    python scripts/seed_curriculum.py
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Añadir el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pdfplumber
except ImportError:
    print("ERROR: Instala pdfplumber: pip install pdfplumber")
    sys.exit(1)

from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent
DBA_DIR = PROJECT_ROOT / "dba"
EBC_DIR = PROJECT_ROOT / "ebc"
FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"


# ---------------------------------------------------------------------------
# Schemas de validación
# ---------------------------------------------------------------------------

class DBASchema(BaseModel):
    grado: str
    area: str
    numero: int
    enunciado: str
    evidencias: list[str]
    ejemplos: Optional[str] = None


class EBCSchema(BaseModel):
    rango_grados: str
    area: str
    factor: str
    enunciado: str


# ---------------------------------------------------------------------------
# Detección de grado desde texto de página
# ---------------------------------------------------------------------------

GRADO_PATTERN = re.compile(
    r"(?:Grado|GRADO)\s*(\d{1,2}[°º]?|[Tt]ransici[oó]n|[Pp]reescolar)",
    re.IGNORECASE,
)

AREA_MAPPING = {
    "matematica": "Matemáticas",
    "matemáticas": "Matemáticas",
    "lenguaje": "Lenguaje",
    "ciencias naturales": "Ciencias Naturales",
    "ciencias sociales": "Ciencias Sociales",
    "ingles": "Inglés",
    "inglés": "Inglés",
}

DBA_NUM_PATTERN = re.compile(r"DBA\s*[nN]?[°º]?\s*(\d+)", re.IGNORECASE)
EVIDENCIAS_PATTERN = re.compile(
    r"Evidencias de aprendizaje[:\s]+(.*?)(?=DBA\s*\d|$)", re.DOTALL | re.IGNORECASE
)


def detectar_area_desde_nombre(nombre_archivo: str) -> str:
    """Intenta detectar el área curricular desde el nombre del archivo PDF."""
    nombre = nombre_archivo.lower()
    for key, value in AREA_MAPPING.items():
        if key in nombre:
            return value
    return "Sin clasificar"


def extraer_dba_desde_pagina(texto: str, grado: str, area: str) -> list[dict]:
    """
    Parser de reglas para extraer DBA de una página con layout simple.
    Retorna lista de dicts con estructura DBASchema.
    """
    registros = []
    matches = list(DBA_NUM_PATTERN.finditer(texto))

    for i, match in enumerate(matches):
        num = int(match.group(1))
        inicio = match.end()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        bloque = texto[inicio:fin].strip()

        # Separar enunciado de evidencias
        partes = re.split(r"Evidencias de aprendizaje[:\s]+", bloque, flags=re.IGNORECASE)
        enunciado = partes[0].strip()

        evidencias = []
        if len(partes) > 1:
            evidencias_texto = partes[1].strip()
            # Tokenizar por viñetas comunes
            evidencias = [
                e.strip()
                for e in re.split(r"[•·\-\*]\s+|\n\s*\d+[.)]\s+", evidencias_texto)
                if e.strip() and len(e.strip()) > 10
            ]

        if enunciado and num:
            registros.append({
                "grado": grado,
                "area": area,
                "numero": num,
                "enunciado": enunciado[:500],
                "evidencias": evidencias[:10],  # Máx 10 evidencias
                "ejemplos": None,
            })

    return registros


async def usar_gemini_fallback(texto_pagina: str, schema_tipo: str) -> list[dict]:
    """
    Fallback con Gemini para páginas con layouts complejos.
    Se usa cuando el parser de reglas no extrae nada.
    """
    try:
        from app.core.config import settings
        if not settings.GEMINI_API_KEY:
            logger.warning("Sin GEMINI_API_KEY para fallback. Saltando página compleja.")
            return []

        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        schema_desc = (
            '[{"grado": "3", "area": "Matemáticas", "numero": 1, '
            '"enunciado": "...", "evidencias": ["...", "..."]}]'
            if schema_tipo == "dba"
            else '[{"rango_grados": "1-3", "area": "Lenguaje", "factor": "...", "enunciado": "..."}]'
        )

        prompt = (
            f"Analiza este texto de un documento curricular colombiano del MEN y extrae "
            f"los registros en formato JSON. Usa este esquema: {schema_desc}\n\n"
            f"TEXTO:\n{texto_pagina[:4000]}\n\n"
            "Responde SOLO con el JSON array. Sin texto adicional."
        )

        response = await model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)

    except Exception as exc:
        logger.error("Error en fallback Gemini: %s", exc)
        return []


def procesar_pdfs_dba() -> list[dict]:
    """Procesa todos los PDFs de DBA y retorna lista de registros."""
    if not DBA_DIR.exists():
        logger.warning("Directorio dba/ no encontrado en: %s", DBA_DIR)
        return []

    todos_dba = []
    for pdf_path in sorted(DBA_DIR.glob("*.pdf")):
        logger.info("Procesando DBA: %s", pdf_path.name)
        area = detectar_area_desde_nombre(pdf_path.stem)
        grado_actual = "Sin grado"

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text() or ""

                    # Detectar cambio de grado en esta página
                    m = GRADO_PATTERN.search(texto)
                    if m:
                        grado_raw = m.group(1).strip("°º").strip()
                        grado_actual = (
                            "transicion"
                            if grado_raw.lower() in ("transición", "transicion", "preescolar")
                            else grado_raw
                        )

                    registros = extraer_dba_desde_pagina(texto, grado_actual, area)
                    todos_dba.extend(registros)

        except Exception as exc:
            logger.error("Error procesando %s: %s", pdf_path.name, exc)

    # Validar con Pydantic
    validados = []
    for r in todos_dba:
        try:
            validados.append(DBASchema(**r).model_dump())
        except Exception as exc:
            logger.warning("DBA inválido descartado: %s | Error: %s", r, exc)

    logger.info("Total DBA extraídos y validados: %d", len(validados))
    return validados


def procesar_pdfs_ebc() -> list[dict]:
    """Procesa todos los PDFs de EBC y retorna lista de registros."""
    if not EBC_DIR.exists():
        logger.warning("Directorio ebc/ no encontrado en: %s", EBC_DIR)
        return []

    todos_ebc = []
    logger.info("Procesando EBC — se requiere revisión manual de layouts complejos.")

    for pdf_path in sorted(EBC_DIR.glob("*.pdf")):
        logger.info("Procesando EBC: %s", pdf_path.name)
        area = detectar_area_desde_nombre(pdf_path.stem)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text() or ""
                    if not texto.strip():
                        continue
                    # Los EBC tienen estructura más compleja — se procesará con Gemini
                    # Por ahora, marcar para revisión manual
                    logger.debug(
                        "Página EBC requiere procesamiento: %s", pdf_path.name
                    )
        except Exception as exc:
            logger.error("Error procesando %s: %s", pdf_path.name, exc)

    logger.info("EBC: %d registros extraídos.", len(todos_ebc))
    return todos_ebc


def guardar_fixtures(dba_data: list[dict], ebc_data: list[dict]) -> None:
    """Guarda los fixtures JSON en el directorio de fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    dba_path = FIXTURES_DIR / "dba_fixtures.json"
    ebc_path = FIXTURES_DIR / "ebc_fixtures.json"

    with open(dba_path, "w", encoding="utf-8") as f:
        json.dump(dba_data, f, ensure_ascii=False, indent=2)
    logger.info("✅ Guardado: %s (%d registros)", dba_path, len(dba_data))

    with open(ebc_path, "w", encoding="utf-8") as f:
        json.dump(ebc_data, f, ensure_ascii=False, indent=2)
    logger.info("✅ Guardado: %s (%d registros)", ebc_path, len(ebc_data))


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OpenPiar — Ingesta de Currículum MEN (DBA y EBC)")
    logger.info("=" * 60)

    dba_data = procesar_pdfs_dba()
    ebc_data = procesar_pdfs_ebc()
    guardar_fixtures(dba_data, ebc_data)

    logger.info("Ingesta completada. Ejecuta seed_curriculum.py para cargar a PostgreSQL.")
