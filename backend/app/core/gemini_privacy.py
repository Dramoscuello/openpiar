# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Minimización y redacción de texto antes de enviarlo a Gemini.

El perfil permitido contiene contexto pedagógico, observaciones sanitizadas y
diagnóstico médico cuando `AI_INCLUDE_MEDICAL_DIAGNOSIS` está activo. No debe
contener nombre, edad, grado, documentos, teléfonos, correos ni direcciones.
"""

import json
import re
from typing import Any, Optional


def _normalizar(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str) if valor else ""
    return str(valor).strip()


def sanitizar_texto_gemini(
    valor: Any,
    limite: int = 3000,
    textos_prohibidos: Optional[list[str]] = None,
) -> str:
    """Redacta contacto, documentos, direcciones y nombres conocidos."""
    texto = _normalizar(valor)
    if not texto:
        return ""

    texto = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", texto)
    texto = re.sub(
        r"(?<!\d)(?:\+?57[\s.-]?)?\d(?:[\s.-]?\d){6,11}(?!\d)",
        "[teléfono o identificador omitido]",
        texto,
    )
    texto = re.sub(
        r"\b(?:CC|TI|RC|CE|PEP|NIT)\s*[:#-]?\s*\d{5,}\b",
        "[documento omitido]",
        texto,
        flags=re.IGNORECASE,
    )
    texto = re.sub(r"\b\d{7,12}\b", "[identificador omitido]", texto)
    texto = re.sub(
        r"\b(?:calle|carrera|cra\.?|cl\.?|kr\.?|avenida|av\.?)\s+[^,.;\n]{1,50}",
        "[dirección omitida]",
        texto,
        flags=re.IGNORECASE,
    )
    for prohibido in textos_prohibidos or []:
        if prohibido and len(prohibido.strip()) >= 3:
            texto = re.sub(
                re.escape(prohibido.strip()),
                "[nombre omitido]",
                texto,
                flags=re.IGNORECASE,
            )
    return texto[:limite]
