# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Script de ingesta adicional de currículum: Inglés, Educación Física, Tecnología e Informática, Educación Artística.

Lee los PDFs correspondientes de dba/ y ebc/, extrae la información estructurada
usando GPT-4o-mini y la anexa a los fixtures JSON existentes.

Uso:
    cd backend
    python scripts/ingest_extra_curriculum.py
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional, List
import pdfplumber
from pydantic import BaseModel
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Rutas
PROJECT_ROOT = Path(__file__).parent.parent.parent
DBA_DIR = PROJECT_ROOT / "dba"
EBC_DIR = PROJECT_ROOT / "ebc"
FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"

# Cargar OpenAI API Key desde .env
def get_openai_key() -> str:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key == "OPENAI_API_KEY":
                        return val.strip()
    return os.environ.get("OPENAI_API_KEY", "")

openai_key = get_openai_key()
if not openai_key:
    logger.error("❌ No se encontró OPENAI_API_KEY en .env de backend o en el entorno.")
    sys.exit(1)

# Inicializar cliente OpenAI
openai_client = OpenAI(api_key=openai_key, base_url="https://api.openai.com/v1")

# Schemas de validación
class DBASchema(BaseModel):
    grado: str
    area: str
    numero: int
    enunciado: str
    evidencias: List[str]
    ejemplos: Optional[str] = None


class DBAExtraction(BaseModel):
    items: List[DBASchema]


class EBCSchema(BaseModel):
    rango_grados: str
    area: str
    factor: str
    enunciado: str


class EBCExtraction(BaseModel):
    items: List[EBCSchema]


sem = asyncio.Semaphore(6)

async def extraer_dba_con_gpt(text: str, detected_grade: str, area: str) -> List[dict]:
    async with sem:
        for attempt in range(3):
            try:
                loop = asyncio.get_running_loop()
                def call_api():
                    return openai_client.beta.chat.completions.parse(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Eres un extractor experto de Derechos Básicos de Aprendizaje (DBA) de Colombia. "
                                    "Analiza el texto de la página del PDF de Inglés y extrae cada DBA estructurado en formato JSON. "
                                    f"Usa como grado por defecto '{detected_grade}' (debe ser un valor simple: 'transicion', '1', '2', ..., '11') y como área por defecto '{area}'. "
                                    "El número es el identificador (ej: 1, 2, 3). El enunciado es la competencia principal. Evidencias de aprendizaje es la lista de viñetas asociadas."
                                )
                            },
                            {"role": "user", "content": f"Texto de la página:\n{text}"}
                        ],
                        response_format=DBAExtraction,
                        timeout=40.0
                    )
                completion = await loop.run_in_executor(None, call_api)
                return [item.model_dump() for item in completion.choices[0].message.parsed.items]
            except Exception as e:
                logger.warning(f"Error extrayendo DBA Inglés (intento {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return []


async def extraer_ebc_con_gpt(text: str, default_range: str, area: str) -> List[dict]:
    async with sem:
        for attempt in range(3):
            try:
                loop = asyncio.get_running_loop()
                def call_api():
                    return openai_client.beta.chat.completions.parse(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Eres un extractor experto de Estándares Básicos de Competencia (EBC) y Orientaciones Pedagógicas de Colombia. "
                                    "Analiza el texto de la página y extrae cada estándar estructurado en formato JSON. "
                                    f"Identifica el rango de grados correspondiente de la página. El formato del rango de grados DEBE ser uno de los siguientes: '1-3', '4-5', '6-7', '8-9', '10-11'. "
                                    f"Si no se especifica de forma obvia en la página, usa como rango de grados por defecto '{default_range}' y como área por defecto '{area}'. "
                                    "El factor es la columna, categoría de competencia o eje principal (ej: 'Expresión artística', 'Tecnología y sociedad', 'Apropiación y uso de la tecnología', 'Competencia motriz', etc.). "
                                    "El enunciado es la competencia o estándar concreto expresado en primera persona que inicia con un verbo (ej: 'Reconozco...', 'Comprendo...', 'Produzco...')."
                                )
                            },
                            {"role": "user", "content": f"Texto de la página:\n{text}"}
                        ],
                        response_format=EBCExtraction,
                        timeout=40.0
                    )
                completion = await loop.run_in_executor(None, call_api)
                return [item.model_dump() for item in completion.choices[0].message.parsed.items]
            except Exception as e:
                logger.warning(f"Error extrayendo EBC {area} (intento {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return []


GRADO_PATTERN = re.compile(
    r"(?:Grado|GRADO|Grade|GRADE)\s*(\d{1,2}[°º]?|[Tt]ransici[oó]n|[Pp]reescolar)",
    re.IGNORECASE,
)

async def procesar_dba_ingles() -> List[dict]:
    logger.info("📂 Buscando PDFs de DBA de Inglés...")
    tareas = []
    
    # 1. DBA Inglés Transición y Primaria
    pdf1 = DBA_DIR / "DBA-TRANSICIÓN-Y-PRIMARIA_Inglés-min.pdf"
    if pdf1.exists():
        logger.info("📄 Preparando DBA Inglés Primaria: %s", pdf1.name)
        try:
            with pdfplumber.open(pdf1) as pdf:
                grado_actual = "Sin grado"
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Detectar cambio de grado
                    m = GRADO_PATTERN.search(text)
                    if m:
                        g_raw = m.group(1).strip("°º").strip().lower()
                        if g_raw in ("transición", "transicion", "preescolar"):
                            grado_actual = "transicion"
                        else:
                            grado_actual = g_raw
                            
                    # Filtrar páginas relevantes de DBA
                    text_lower = text.lower()
                    if ("al finalizar" in text_lower or "dba" in text_lower or "evidencias" in text_lower) and len(text) > 300:
                        tareas.append(extraer_dba_con_gpt(text, grado_actual, "Inglés"))
        except Exception as e:
            logger.error("Error al leer %s: %s", pdf1.name, e)

    # 2. DBA Inglés Bachillerato (6-11)
    pdf2 = DBA_DIR / "DBA-ingles-espanol.pdf"
    if pdf2.exists():
        logger.info("📄 Preparando DBA Inglés Secundaria: %s", pdf2.name)
        try:
            with pdfplumber.open(pdf2) as pdf:
                grado_actual = "Sin grado"
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Detectar cambio de grado
                    m = GRADO_PATTERN.search(text)
                    if m:
                        g_raw = m.group(1).strip("°º").strip().lower()
                        grado_actual = g_raw
                        
                    text_lower = text.lower()
                    if ("grado" in text_lower or "evidencias" in text_lower) and len(text) > 300 and ("grados 6" in text_lower or "grado 6" in text_lower or "grado 7" in text_lower or "grado 8" in text_lower or "grado 9" in text_lower or "grado 10" in text_lower or "grado 11" in text_lower or "al finalizar" in text_lower):
                        # Solo procesar páginas que contienen DBA
                        if "grados de 6" in text_lower or "introducción" in text_lower or "justificación" in text_lower:
                            continue
                        tareas.append(extraer_dba_con_gpt(text, grado_actual, "Inglés"))
        except Exception as e:
            logger.error("Error al leer %s: %s", pdf2.name, e)

    logger.info("🚀 Enviando %d páginas DBA Inglés a la API de OpenAI...", len(tareas))
    resultados = await asyncio.gather(*tareas)
    
    todos_dba = []
    for grupo in resultados:
        for r in grupo:
            try:
                r["grado"] = str(r["grado"]).replace("°", "").strip().lower()
                todos_dba.append(DBASchema(**r).model_dump())
            except Exception as e:
                logger.debug("DBA Inglés inválido omitido: %s | Error: %s", r, e)
    return todos_dba


async def procesar_ebc_adicionales() -> List[dict]:
    logger.info("📂 Procesando estándares adicionales (Inglés, Educación Física, Tecnología, Artística)...")
    tareas = []
    
    config_adicionales = [
        {"file": "EBC EDUCACIÓN FÍSICA.pdf", "area": "Educación Física", "default_range": "1-3"},
        {"file": "Estandares_Basicos_Competencia_en_Lenguas_Extranjeras_ Ingles-min.pdf", "area": "Inglés", "default_range": "1-3"},
        {"file": "ORIENTACIONES PEDAGÓGICAS EN TECNOLOGÍA E INFORMÁTICA.pdf", "area": "Tecnología e Informática", "default_range": "1-3"},
        {"file": "ORIENTACIONES PEDAGÓGICAS PARA LA EDUCACIÓN ARTÍSTICA.pdf", "area": "Educación Artística", "default_range": "1-3"}
    ]
    
    for config in config_adicionales:
        pdf_path = EBC_DIR / config["file"]
        if not pdf_path.exists():
            logger.warning("⚠️  PDF EBC no encontrado: %s", config["file"])
            continue
            
        logger.info("📄 Preparando EBC: %s", pdf_path.name)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    text_lower = text.lower()
                    
                    # Filtro inteligente de páginas con estándares (evita índices, bibliografía, etc.)
                    has_standard_indicators = (
                        "estándar" in text_lower or 
                        "competencia" in text_lower or 
                        "desempeño" in text_lower or 
                        "ejes" in text_lower or
                        "orientaciones" in text_lower
                    ) and ("•" in text or "-" in text or "*" in text or "✔" in text)
                    
                    if has_standard_indicators and len(text) > 350:
                        if "bibliografía" in text_lower or "referencias" in text_lower or "tabla de contenido" in text_lower:
                            continue
                        tareas.append(extraer_ebc_con_gpt(text, config["default_range"], config["area"]))
        except Exception as e:
            logger.error("Error al abrir PDF EBC %s: %s", config["file"], e)
            
    logger.info("🚀 Enviando %d páginas EBC adicionales a la API de OpenAI...", len(tareas))
    resultados = await asyncio.gather(*tareas)
    
    todos_ebc = []
    for grupo in resultados:
        for r in grupo:
            try:
                todos_ebc.append(EBCSchema(**r).model_dump())
            except Exception as e:
                logger.debug("EBC adicional inválido omitido: %s | Error: %s", r, e)
    return todos_ebc


def anexar_y_guardar_fixtures(dba_nuevos: list, ebc_nuevos: list) -> None:
    dba_path = FIXTURES_DIR / "dba_fixtures.json"
    ebc_path = FIXTURES_DIR / "ebc_fixtures.json"
    
    # 1. Cargar existentes o inicializar
    dba_data = []
    if dba_path.exists():
        try:
            with open(dba_path, "r", encoding="utf-8") as f:
                dba_data = json.load(f)
        except Exception as e:
            logger.error("Error cargando dba_fixtures.json existente: %s", e)
            
    ebc_data = []
    if ebc_path.exists():
        try:
            with open(ebc_path, "r", encoding="utf-8") as f:
                ebc_data = json.load(f)
        except Exception as e:
            logger.error("Error cargando ebc_fixtures.json existente: %s", e)

    # 2. Anexar y deducir duplicados
    # Dba existentes
    dba_keys = {(d["grado"], d["area"], d["numero"], d["enunciado"][:50]) for d in dba_data}
    for d in dba_nuevos:
        key = (d["grado"], d["area"], d["numero"], d["enunciado"][:50])
        if key not in dba_keys:
            dba_data.append(d)
            dba_keys.add(key)
            
    # Ebc existentes
    ebc_keys = {(e["rango_grados"], e["area"], e["factor"], e["enunciado"][:50]) for e in ebc_data}
    for e in ebc_nuevos:
        key = (e["rango_grados"], e["area"], e["factor"], e["enunciado"][:50])
        if key not in ebc_keys:
            ebc_data.append(e)
            ebc_keys.add(key)

    # 3. Guardar actualizados
    with open(dba_path, "w", encoding="utf-8") as f:
        json.dump(dba_data, f, ensure_ascii=False, indent=2)
    logger.info("💾 Fixture Actualizado: dba_fixtures.json (Total registros: %d)", len(dba_data))
    
    with open(ebc_path, "w", encoding="utf-8") as f:
        json.dump(ebc_data, f, ensure_ascii=False, indent=2)
    logger.info("💾 Fixture Actualizado: ebc_fixtures.json (Total registros: %d)", len(ebc_data))


async def main():
    logger.info("=" * 60)
    logger.info("OpenPiar — Ingesta de Áreas Adicionales (Inglés, Deportes, Artes, Tecnología)")
    logger.info("=" * 60)
    
    dba_nuevos = await procesar_dba_ingles()
    ebc_nuevos = await procesar_ebc_adicionales()
    
    anexar_y_guardar_fixtures(dba_nuevos, ebc_nuevos)
    logger.info("✨ Ingesta de áreas adicionales completada exitosamente.")
    logger.info("👉 Ejecuta 'python scripts/seed_curriculum.py' para cargarlos a la base de datos.")


if __name__ == "__main__":
    asyncio.run(main())
