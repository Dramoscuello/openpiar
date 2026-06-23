# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Script de ingesta de currículum: DBA y EBC.

Lee los PDFs oficiales del MEN desde las carpetas dba/ y ebc/
del proyecto raíz, extrae la información estructurada usando pdfplumber
y GPT-4o-mini (OpenAI Structured Outputs), y guarda los fixtures JSON.

Uso:
    cd backend
    python scripts/ingest_curriculum.py
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

# Inicializar cliente OpenAI (se fuerza base_url para evitar redirecciones a Ollama local)
openai_client = OpenAI(api_key=openai_key, base_url="https://api.openai.com/v1")

# ---------------------------------------------------------------------------
# Schemas de validación (Pydantic v2)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Mapeos y Configuración
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
    "naturales": "Ciencias Naturales",
    "sociales": "Ciencias Sociales",
}

def detectar_area_desde_nombre(nombre_archivo: str) -> str:
    nombre = nombre_archivo.lower()
    for key, value in AREA_MAPPING.items():
        if key in nombre:
            return value
    return "Sin clasificar"


# Mapeo preciso de páginas del PDF de EBC
EBC_PAGES_MAP = [
    # Lenguaje
    {"index": 31, "area": "Lenguaje", "rango": "1-3"},
    {"index": 32, "area": "Lenguaje", "rango": "1-3"},
    {"index": 33, "area": "Lenguaje", "rango": "4-5"},
    {"index": 34, "area": "Lenguaje", "rango": "4-5"},
    {"index": 35, "area": "Lenguaje", "rango": "6-7"},
    {"index": 36, "area": "Lenguaje", "rango": "6-7"},
    {"index": 37, "area": "Lenguaje", "rango": "8-9"},
    {"index": 38, "area": "Lenguaje", "rango": "8-9"},
    {"index": 39, "area": "Lenguaje", "rango": "10-11"},
    {"index": 40, "area": "Lenguaje", "rango": "10-11"},
    # Matemáticas
    {"index": 79, "area": "Matemáticas", "rango": "1-3"},
    {"index": 80, "area": "Matemáticas", "rango": "1-3"},
    {"index": 81, "area": "Matemáticas", "rango": "4-5"},
    {"index": 82, "area": "Matemáticas", "rango": "4-5"},
    {"index": 83, "area": "Matemáticas", "rango": "6-7"},
    {"index": 84, "area": "Matemáticas", "rango": "6-7"},
    {"index": 85, "area": "Matemáticas", "rango": "8-9"},
    {"index": 86, "area": "Matemáticas", "rango": "8-9"},
    {"index": 87, "area": "Matemáticas", "rango": "10-11"},
    {"index": 88, "area": "Matemáticas", "rango": "10-11"},
    # Ciencias Sociales
    {"index": 121, "area": "Ciencias Sociales", "rango": "1-3"},
    {"index": 123, "area": "Ciencias Sociales", "rango": "4-5"},
    {"index": 125, "area": "Ciencias Sociales", "rango": "6-7"},
    {"index": 127, "area": "Ciencias Sociales", "rango": "8-9"},
    {"index": 129, "area": "Ciencias Sociales", "rango": "10-11"},
    # Ciencias Naturales
    {"index": 131, "area": "Ciencias Naturales", "rango": "1-3"},
    {"index": 133, "area": "Ciencias Naturales", "rango": "4-5"},
    {"index": 135, "area": "Ciencias Naturales", "rango": "6-7"},
    {"index": 137, "area": "Ciencias Naturales", "rango": "8-9"},
    {"index": 139, "area": "Ciencias Naturales", "rango": "10-11"},
]

# Semáforo para controlar concurrencia a la API de OpenAI
sem = asyncio.Semaphore(6)

# ---------------------------------------------------------------------------
# Llamadas estructuradas con GPT-4o-mini
# ---------------------------------------------------------------------------

async def extraer_dba_con_gpt(text: str, detected_grade: str, default_area: str) -> List[dict]:
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
                                    "Analiza el texto de la página del PDF provisto y extrae cada DBA estructurado en formato JSON. "
                                    f"Usa como grado por defecto '{detected_grade}' (debe ser un valor simple: 'transicion', '1', '2', ..., '11') y como área por defecto '{default_area}'. "
                                    "Si el texto pertenece a transición, clasifica dinámicamente el área de cada DBA en una de estas cuatro categorías de acuerdo a su temática: "
                                    "'Matemáticas', 'Lenguaje', 'Ciencias Naturales' o 'Ciencias Sociales'. "
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
                logger.warning(f"Error extrayendo DBA (intento {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return []


async def extraer_ebc_con_gpt(text: str, rango_grados: str, area: str) -> List[dict]:
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
                                    "Eres un extractor experto de Estándares Básicos de Competencia (EBC) de Colombia. "
                                    "Analiza el texto de la página del PDF provisto y extrae cada estándar en formato JSON. "
                                    f"Usa como rango_grados '{rango_grados}' y como área '{area}'. "
                                    "El factor es la columna o categoría de competencia principal de la página (ej: 'PRODUCCIÓN TEXTUAL', 'COMPRENSIÓN E INTERPRETACIÓN TEXTUAL', 'LITERATURA', "
                                    "'PENSAMIENTO NUMÉRICO Y SISTEMAS NUMÉRICOS', 'Me aproximo al conocimiento como científico(a) natural', etc.). "
                                    "El enunciado es el estándar concreto redactado en primera persona que inicia con un verbo (ej: 'Produzco textos escritos...', 'Reconozco significados...')."
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
                logger.warning(f"Error extrayendo EBC (intento {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return []


# ---------------------------------------------------------------------------
# Procesamiento de PDF
# ---------------------------------------------------------------------------

async def procesar_dbas() -> List[dict]:
    if not DBA_DIR.exists():
        logger.warning("❌ Directorio dba/ no encontrado en: %s", DBA_DIR)
        return []

    logger.info("📂 Escaneando directorio DBA en búsqueda de PDFs...")
    tareas = []
    
    for pdf_path in sorted(DBA_DIR.glob("*.pdf")):
        if pdf_path.name.startswith("."):
            continue
        
        # Ignorar PDFs de inglés ya que no están contemplados en el dominio del PIAR (ck_ajustes_area)
        if "ingle" in pdf_path.name.lower():
            logger.info("⏩ Saltando PDF de Inglés: %s", pdf_path.name)
            continue
            
        logger.info("📄 Preparando DBA: %s", pdf_path.name)
        area_por_defecto = detectar_area_desde_nombre(pdf_path.stem)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                grado_actual = "Sin grado"
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Detectar cambio de grado en la página
                    m = GRADO_PATTERN.search(text)
                    if m:
                        g_raw = m.group(1).strip("°º").strip().lower()
                        if g_raw in ("transición", "transicion", "preescolar"):
                            grado_actual = "transicion"
                        else:
                            grado_actual = g_raw
                    
                    # Filtrar páginas que no tengan contenido real de DBA
                    text_lower = text.lower()
                    contiene_dba = "evidencias de aprendizaje" in text_lower or "ejemplo" in text_lower or "derechos básicos de aprendizaje" in text_lower
                    
                    if contiene_dba and len(text) > 350:
                        tareas.append(extraer_dba_con_gpt(text, grado_actual, area_por_defecto))
                        
        except Exception as exc:
            logger.error("Error al abrir %s: %s", pdf_path.name, exc)
            
    logger.info("🚀 Enviando %d páginas DBA a la API de OpenAI...", len(tareas))
    resultados = await asyncio.gather(*tareas)
    
    # Consolidar y validar
    todos_dba = []
    for grupo in resultados:
        for r in grupo:
            try:
                # Limpieza de grado
                r["grado"] = str(r["grado"]).replace("°", "").strip().lower()
                # Validación estricta con Pydantic
                todos_dba.append(DBASchema(**r).model_dump())
            except Exception as e:
                logger.debug("DBA inválido omitido: %s | Error: %s", r, e)
                
    logger.info("✅ Procesados y validados %d registros de DBA.", len(todos_dba))
    return todos_dba


async def procesar_ebcs() -> List[dict]:
    if not EBC_DIR.exists():
        logger.warning("❌ Directorio ebc/ no encontrado en: %s", EBC_DIR)
        return []

    # Buscamos el PDF de lenguaje, matemáticas, ciencias naturales y sociales del MEN
    ebc_pdf_path = next(EBC_DIR.glob("*Lenguaje*Matem*Ciencias*.pdf"), None)
    if not ebc_pdf_path:
        logger.warning("❌ No se encontró el PDF principal de EBC en %s", EBC_DIR)
        return []

    logger.info("📄 Preparando EBC principal: %s", ebc_pdf_path.name)
    tareas = []
    
    try:
        with pdfplumber.open(ebc_pdf_path) as pdf:
            for item in EBC_PAGES_MAP:
                page_idx = item["index"]
                if page_idx >= len(pdf.pages):
                    continue
                    
                page = pdf.pages[page_idx]
                text = page.extract_text() or ""
                
                if text.strip():
                    tareas.append(extraer_ebc_con_gpt(text, item["rango"], item["area"]))
                    
    except Exception as exc:
        logger.error("Error al abrir PDF EBC: %s", exc)

    logger.info("🚀 Enviando %d páginas EBC a la API de OpenAI...", len(tareas))
    resultados = await asyncio.gather(*tareas)
    
    # Consolidar y validar
    todos_ebc = []
    for grupo in resultados:
        for r in grupo:
            try:
                todos_ebc.append(EBCSchema(**r).model_dump())
            except Exception as e:
                logger.debug("EBC inválido omitido: %s | Error: %s", r, e)
                
    logger.info("✅ Procesados y validados %d registros de EBC.", len(todos_ebc))
    return todos_ebc


def guardar_fixtures(dba_data: list, ebc_data: list) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    dba_path = FIXTURES_DIR / "dba_fixtures.json"
    ebc_path = FIXTURES_DIR / "ebc_fixtures.json"
    
    with open(dba_path, "w", encoding="utf-8") as f:
        json.dump(dba_data, f, ensure_ascii=False, indent=2)
    logger.info("💾 Guardado: %s (%d registros)", dba_path.name, len(dba_data))
    
    with open(ebc_path, "w", encoding="utf-8") as f:
        json.dump(ebc_data, f, ensure_ascii=False, indent=2)
    logger.info("💾 Guardado: %s (%d registros)", ebc_path.name, len(ebc_data))


async def main():
    logger.info("=" * 60)
    logger.info("OpenPiar — Ingesta Inteligente de Currículo MEN (DBA y EBC)")
    logger.info("=" * 60)
    
    dba_data = await procesar_dbas()
    ebc_data = await procesar_ebcs()
    
    guardar_fixtures(dba_data, ebc_data)
    logger.info("✨ Ingesta completada con éxito.")
    logger.info("👉 Ejecuta 'python scripts/seed_curriculum.py' para cargarlos a la base de datos.")


if __name__ == "__main__":
    asyncio.run(main())
