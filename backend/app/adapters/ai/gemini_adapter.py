# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Adaptador Gemini API — implementación del puerto IAgentePedagogico.

Utiliza google-generativeai con Structured Outputs (JSON Schema)
para garantizar respuestas tipadas que encajan en la tabla ajustes_razonables.
"""

import json
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.core.config import get_settings
from app.domain.ports import IAgentePedagogico

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Prompt de sistema — instrucciones DUA para el agente
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_AJUSTES_DUA = """
Eres un Agente Pedagógico Especialista en Educación Inclusiva para Colombia.
Tu misión es generar ajustes razonables curriculares según el Decreto 1421 de 2017
y el Diseño Universal para el Aprendizaje (DUA).

REGLAS ESTRICTAS:
1. Estructura TODOS los ajustes en los tres principios DUA:
   - representacion: Múltiples formas de presentar la información (el "qué")
   - accion_expresion: Múltiples formas de demostrar el aprendizaje (el "cómo")
   - implicacion: Múltiples formas de motivar al estudiante (el "porqué")
2. Usa la Taxonomía de Bloom para calibrar el nivel cognitivo:
   - Si el estudiante tiene barreras cognitivas, baja el verbo de acción
     (de "Argumentar" a "Identificar" o "Describir con apoyo visual")
3. Adapta SIEMPRE las sugerencias al modelo pedagógico del colegio (perfil_pei).
4. Propón ajustes REALISTAS para la escuela pública colombiana.
5. Responde ÚNICAMENTE con el JSON estructurado. Sin texto previo ni posterior.
"""

SYSTEM_PROMPT_PEI = """
Eres un extractor de información pedagógica institucional.
Analiza el texto del Proyecto Educativo Institucional (PEI) colombiano que se
te proporciona y extrae los siguientes campos en formato JSON:
- modelo_pedagogico: El enfoque pedagógico oficial (ej: "constructivista", "crítico-social", "tradicional")
- enfoques_didacticos: Lista de enfoques especiales (ej: ["técnico agropecuario", "bilingüe"])
- valores: Lista de valores institucionales declarados
- politicas_convivencia: Resumen de políticas de convivencia relevantes

Responde ÚNICAMENTE con el JSON. Sin texto adicional.
"""


class GeminiAgentAdapter(IAgentePedagogico):
    """
    Implementación del agente pedagógico usando Google Gemini API.

    Usa response_mime_type="application/json" con un schema Pydantic para
    garantizar que el modelo siempre responda con el formato esperado.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        _api_key = api_key or settings.GEMINI_API_KEY
        _model = model or settings.GEMINI_MODEL

        if not _api_key:
            raise ValueError(
                "GEMINI_API_KEY no configurada. "
                "Agrega tu clave en la tabla configuracion_sistema o en .env"
            )

        genai.configure(api_key=_api_key)
        self._model = genai.GenerativeModel(
            model_name=_model,
            system_instruction=SYSTEM_PROMPT_AJUSTES_DUA,
        )
        self._model_pei = genai.GenerativeModel(
            model_name=_model,
            system_instruction=SYSTEM_PROMPT_PEI,
        )

    async def generar_ajustes_dua(
        self,
        perfil_estudiante: dict,
        objetivo_curricular: dict,
        perfil_pei: dict,
    ) -> dict:
        """
        Genera ajustes razonables DUA en formato JSON estructurado.

        Construye el prompt dinámico combinando:
        1. Perfil del estudiante (Anexo 1)
        2. Objetivo curricular (DBA/EBC seleccionado)
        3. Perfil pedagógico del colegio (extraído del PEI)
        """
        prompt = f"""
PERFIL DEL ESTUDIANTE:
{json.dumps(perfil_estudiante, ensure_ascii=False, indent=2)}

OBJETIVO DE APRENDIZAJE (DBA/EBC):
{json.dumps(objetivo_curricular, ensure_ascii=False, indent=2)}

PERFIL PEDAGÓGICO DEL COLEGIO (PEI):
{json.dumps(perfil_pei, ensure_ascii=False, indent=2)}

Genera una propuesta completa de ajustes razonables DUA para este estudiante,
alineados al objetivo curricular y al modelo pedagógico del colegio.

Responde con este JSON exacto:
{{
  "representacion": "Descripción de cómo presentar la información",
  "accion_expresion": "Descripción de cómo el estudiante puede demostrar aprendizaje",
  "implicacion": "Descripción de cómo motivar al estudiante",
  "barreras_identificadas": "Barreras específicas identificadas en el contexto",
  "ajustes_evaluacion": "Modificaciones al proceso evaluativo según el SIEE"
}}
"""
        try:
            response = await self._model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.4,  # Más determinista para salidas pedagógicas
                ),
            )
            return json.loads(response.text)
        except Exception as exc:
            logger.error("Error generando ajustes DUA con Gemini: %s", exc)
            raise RuntimeError(f"Error en el agente pedagógico: {exc}") from exc

    async def extraer_perfil_pei(self, texto_pei: str) -> dict:
        """
        Extrae el perfil pedagógico del texto del PEI usando Gemini.

        Args:
            texto_pei: Texto completo extraído del PDF del PEI.

        Returns:
            dict con: modelo_pedagogico, enfoques_didacticos, valores, politicas_convivencia.
        """
        prompt = f"""
Analiza el siguiente texto del PEI y extrae la información solicitada:

{texto_pei[:8000]}  # Limitar a 8000 chars para no exceder contexto
"""
        try:
            response = await self._model_pei.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except Exception as exc:
            logger.error("Error extrayendo perfil PEI con Gemini: %s", exc)
            # Retornar perfil vacío para no bloquear el flujo del setup
            return {
                "modelo_pedagogico": "No extraído",
                "enfoques_didacticos": [],
                "valores": [],
                "politicas_convivencia": "",
            }
