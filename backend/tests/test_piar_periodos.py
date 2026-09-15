# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""PIAR por periodo académico: helpers puros y validaciones de periodo."""

from types import SimpleNamespace as NS

import pytest

from app.entrypoints.api.schemas import PeriodoAcademicoCreate
from app.entrypoints.api.v1.endpoints import piars


def _piar_periodos():
    return NS(
        id="piar-1",
        estudiante_id="est-1",
        anio_lectivo=2026,
        fecha_creacion=None,
        estado="borrador",
        periodos=[
            NS(periodo_id=1, estado="firmado"),
            NS(periodo_id=2, estado="borrador"),
        ],
        actas_acuerdo=[
            NS(periodo_id=1, compromisos_casa=[], fecha_firma=None, compromisos_aula=None,
               firmado_estudiante=False, firmado_acudiente=False, firmado_docente_apoyo=False,
               firmado_docentes_aula=False, firmado_directivo=False),
            NS(periodo_id=2, compromisos_casa=[], fecha_firma=None, compromisos_aula=None,
               firmado_estudiante=False, firmado_acudiente=False, firmado_docente_apoyo=False,
               firmado_docentes_aula=False, firmado_directivo=False),
        ],
        asignaturas_estado=[
            NS(periodo_id=1, asignatura_id="math", nombre_asignatura="Matemáticas",
               area_nombre="Matemáticas", docente_id="d1", docente_nombre="Docente Uno",
               estado="con_ajuste", justificacion=None),
            NS(periodo_id=2, asignatura_id="math", nombre_asignatura="Matemáticas",
               area_nombre="Matemáticas", docente_id="d1", docente_nombre="Docente Uno",
               estado="pendiente", justificacion=None),
        ],
        ajustes_razonables=[
            NS(periodo_id=1, asignatura_id="math", area="Matemáticas",
               titulo_tema="Tema 1", objetivos_propositos="Uno", barreras_evidenciadas="B1",
               tipo_ajuste="T", apoyo_requerido="A", ajustes_estrategias="E",
               evaluacion_ajustes=None, puntuacion=None, comentario_puntuacion=None,
               temporalidad=None, responsable=None, medios_verificacion=None,
               dba_referencia=None),
            NS(periodo_id=2, asignatura_id="math", area="Matemáticas",
               titulo_tema="Tema 2", objetivos_propositos="Dos", barreras_evidenciadas="B2",
               tipo_ajuste="T", apoyo_requerido="A", ajustes_estrategias="E",
               evaluacion_ajustes=None, puntuacion=None, comentario_puntuacion=None,
               temporalidad=None, responsable=None, medios_verificacion=None,
               dba_referencia=None),
        ],
        estudiante=NS(
            entorno_salud=None, entorno_hogar=None, trayectoria_educativa=None,
            matricula_actual=None, grupo=None,
        ),
        caracteristicas=None,
        participantes=[],
        lugar_diligenciamiento="Bogotá",
    )


def test_periodo_valida_anio_y_fechas():
    with pytest.raises(ValueError):
        PeriodoAcademicoCreate(
            nombre="Periodo inválido", anio_lectivo=2026,
            fecha_inicio="2026-06-01", fecha_fin="2026-05-01",
        )

    valido = PeriodoAcademicoCreate(
        nombre="Primer periodo", anio_lectivo=2026,
        fecha_inicio="2026-01-20", fecha_fin="2026-04-15",
    )
    assert valido.anio_lectivo == 2026

    with pytest.raises(ValueError):
        PeriodoAcademicoCreate(
            nombre="Sin año", anio_lectivo=1999,
            fecha_inicio="2026-01-20", fecha_fin="2026-04-15",
        )


def test_estado_y_acta_se_resuelven_por_periodo():
    piar = _piar_periodos()

    assert piars._estado_periodo(piar, 1) == "firmado"
    assert piars._estado_periodo(piar, 2) == "borrador"
    assert piars._estado_periodo(piar, 99) == "borrador"
    assert piars._estado_periodo(piar, None) == "borrador"

    assert piars._acta_del_periodo(piar, 1).periodo_id == 1
    assert piars._acta_del_periodo(piar, 2).periodo_id == 2
    assert piars._acta_del_periodo(piar, 99) is None


def test_registro_piar_periodo_reutiliza_o_crea():
    piar = _piar_periodos()

    existente = piars._piar_periodo(piar, 1)
    assert existente.estado == "firmado"
    assert len(piar.periodos) == 2

    nuevo = piars._piar_periodo(piar, 3)
    assert nuevo.estado == "borrador"
    assert len(piar.periodos) == 3
    assert piars._piar_periodo(piar, 3) is nuevo


def test_datos_completitud_filtra_ajustes_cobertura_y_acta_del_periodo():
    datos = piars._datos_completitud(_piar_periodos(), periodo_id=2)

    assert [item["objetivos_propositos"] for item in datos.ajustes] == ["Dos"]
    assert [item["estado"] for item in datos.asignaturas] == ["pendiente"]
    assert datos.acta is not None
    assert datos.acta["firmado_estudiante"] is False

    datos_p1 = piars._datos_completitud(_piar_periodos(), periodo_id=1)
    assert [item["objetivos_propositos"] for item in datos_p1.ajustes] == ["Uno"]
    assert [item["estado"] for item in datos_p1.asignaturas] == ["con_ajuste"]


def test_snapshot_incluye_periodo_y_solo_ajustes_del_periodo():
    snapshot = piars._snapshot_piar(_piar_periodos(), periodo_id=2)

    assert snapshot["periodo_id"] == 2
    assert len(snapshot["ajustes"]) == 1
    assert snapshot["ajustes"][0]["objetivos_propositos"] == "Dos"
