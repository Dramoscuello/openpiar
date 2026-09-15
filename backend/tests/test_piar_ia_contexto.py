# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Contexto de IA del PIAR: campos opcionales, overrides del formulario y PEI."""

from types import SimpleNamespace as NS

from app.entrypoints.api.v1.endpoints.piars import (
    construir_contexto_estudiante,
    construir_contexto_institucional,
)


def _piar_completo():
    return NS(
        estudiante=NS(entorno_salud=NS(diagnostico_medico="Dislexia")),
        caracteristicas=NS(
            descripcion_gustos_intereses="Dinosaurios y dibujo",
            expectativas_estudiante="Aprender a leer",
            expectativas_familia="Integrarse con sus pares",
            descripcion_habilidades="Memoria visual",
            redes_apoyo="Abuela",
            entorno_familiar_social_economico="Entorno estable",
            otras_observaciones="Participa en teatro",
            caracterizacion_pedagogica="Requiere apoyos visuales",
        ),
    )


def test_contexto_estudiante_incluye_los_campos_solicitados():
    contexto = construir_contexto_estudiante(_piar_completo())

    esperados = {
        "Gustos, intereses y expectativas del estudiante y su familia": [
            "Dinosaurios y dibujo",
            "Aprender a leer",
            "Integrarse con sus pares",
        ],
        "Habilidades, cualidades, fortalezas y apoyos requeridos": [
            "Memoria visual",
            "Abuela",
        ],
        "Entorno familiar, social y económico": ["Entorno estable"],
        "Otras observaciones": ["Participa en teatro"],
        "Caracterización pedagógica / Diagnóstico": ["Requiere apoyos visuales"],
        "Diagnóstico médico": ["Dislexia"],
    }
    for etiqueta, valores in esperados.items():
        assert f"- {etiqueta}: " in contexto
        for valor in valores:
            assert valor in contexto


def test_contexto_estudiante_tolera_campos_vacios_y_relaciones_ausentes():
    assert construir_contexto_estudiante(None) == "- Sin información registrada."

    vacio = NS(estudiante=NS(entorno_salud=None), caracteristicas=None)
    assert construir_contexto_estudiante(vacio) == "- Sin información registrada."

    parcial = NS(
        estudiante=None,
        caracteristicas=NS(
            descripcion_gustos_intereses="Música",
            descripcion_habilidades=None,
            entorno_familiar_social_economico="",
            otras_observaciones=None,
            caracterizacion_pedagogica="   ",
            expectativas_estudiante=None,
            expectativas_familia=None,
        ),
    )
    contexto = construir_contexto_estudiante(parcial)
    assert "Música" in contexto
    assert "Habilidades, cualidades" not in contexto
    assert "Entorno familiar" not in contexto
    assert "Diagnóstico médico" not in contexto


def test_contexto_estudiante_prioriza_los_overrides_del_formulario():
    contexto = construir_contexto_estudiante(
        _piar_completo(),
        {
            "gustos_intereses": "Ajedrez (sin guardar)",
            "diagnostico_medico": "TDAH",
            "entorno_familiar_social_economico": "Contexto editado",
        },
    )

    assert "Ajedrez (sin guardar)" in contexto
    assert "Dinosaurios y dibujo" not in contexto
    assert "TDAH" in contexto
    assert "Dislexia" not in contexto
    assert "Contexto editado" in contexto
    assert "Entorno estable" not in contexto


def test_contexto_institucional_incluye_pei_y_serializa_estructuras():
    config = NS(
        pei_modelo_pedagogico="Constructivista",
        pei_valores_principios={"valores": ["Respeto", "Inclusión"]},
        contexto_institucion="Colegio rural con conectividad limitada",
    )
    contexto = construir_contexto_institucional(config)

    assert "Modelo pedagógico del PEI: Constructivista" in contexto
    assert "Valores y principios del PEI:" in contexto
    assert "Respeto" in contexto and "Inclusión" in contexto
    assert "Colegio rural con conectividad limitada" in contexto


def test_contexto_institucional_tolera_configuracion_ausente_o_vacia():
    assert construir_contexto_institucional(None) == "Sin contexto institucional registrado."

    config = NS(
        pei_modelo_pedagogico=None,
        pei_valores_principios=None,
        contexto_institucion="",
    )
    assert construir_contexto_institucional(config) == "Sin contexto institucional registrado."
