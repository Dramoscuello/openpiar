# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Contratos OpenAPI del registro mínimo y del flujo PIAR versionado."""

from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.main import app
from app.entrypoints.api.schemas import (
    AjusteRazonableCreate, GenerarPlanCompletoRequest, PiarAsignaturaEstadoUpdate,
)
from app.entrypoints.api.v1.endpoints import piars
from app.entrypoints.api.v1.endpoints.piars import (
    _exigir_permiso_asignatura,
    _exigir_piar_editable,
)


def test_contratos_principales_del_flujo_piar():
    schema = app.openapi()
    paths = schema["paths"]

    assert "post" in paths["/api/v1/estudiantes/"]
    assert "patch" in paths["/api/v1/estudiantes/{estudiante_id}"]
    assert "get" in paths["/api/v1/piars/estudiante/{estudiante_id}"]
    assert "get" in paths["/api/v1/piars/{piar_id}/completitud"]
    assert "patch" in paths["/api/v1/piars/{piar_id}/asignaturas/{asignatura_id}"]
    assert "get" in paths["/api/v1/piars/{piar_id}/pdf"]
    assert "post" in paths["/api/v1/piars/{piar_id}/finalizar"]
    assert "post" in paths["/api/v1/piars/{piar_id}/reabrir"]

    crear = schema["components"]["schemas"]["CrearEstudianteRequest"]
    assert set(crear["required"]) == {
        "nombres", "apellidos", "tipo_documento", "numero_documento",
        "fecha_nacimiento", "grupo_id",
    }
    for opcional in ("direccion", "telefono", "correo", "municipio_residencia"):
        assert opcional not in crear["required"]

    pdf_params = paths["/api/v1/piars/{piar_id}/pdf"]["get"]["parameters"]
    modo = next(param for param in pdf_params if param["name"] == "modo")
    assert modo["schema"]["pattern"] == "^(borrador|final)$"


def test_ajuste_e_ia_aceptan_ausencia_de_campos_ocultos():
    ajuste = AjusteRazonableCreate(
        area="Matemáticas", objetivos_propositos="Sumar cantidades",
        barreras_evidenciadas="Texto denso", ajustes_estrategias="Usar objetos",
        tipo_ajuste="Didáctico", apoyo_requerido="Material concreto",
    )
    for campo in ("temporalidad", "responsable", "medios_verificacion", "dba_referencia"):
        assert getattr(ajuste, campo) is None
    generacion = GenerarPlanCompletoRequest(
        area="Matemáticas", estudiante_nombre="Estudiante de prueba",
        barreras_evidenciadas="Texto denso",
    )
    assert generacion.dba_referencia is None
    assert generacion.ebc_referencia is None


def test_permisos_de_asignatura_y_bloqueo_de_version_final():
    cobertura = NS(docente_id="docente-asignado")
    docente_asignado = NS(id="docente-asignado", rol=NS(es_directivo=False))
    docente_ajeno = NS(id="docente-ajeno", rol=NS(es_directivo=False))
    directivo = NS(id="directivo", rol=NS(es_directivo=True))

    _exigir_permiso_asignatura(cobertura, docente_asignado)
    with pytest.raises(HTTPException) as error_directivo:
        _exigir_permiso_asignatura(cobertura, directivo)
    assert error_directivo.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        _exigir_permiso_asignatura(cobertura, docente_ajeno)
    assert error.value.status_code == 403

    with pytest.raises(HTTPException) as error_final:
        _exigir_piar_editable(NS(estado="firmado"))
    assert error_final.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("rol", ["docente", "director", "directivo"])
@pytest.mark.parametrize("estado", ["pendiente", "no_requiere"])
async def test_cobertura_rechaza_suplir_al_docente(monkeypatch, rol, estado):
    usuario_id, docente_id, asignatura_id = uuid4(), uuid4(), uuid4()
    cobertura = NS(asignatura_id=asignatura_id, docente_id=docente_id,
                   estado="no_requiere", justificacion="Justificación del docente")
    piar = NS(estado="borrador", asignaturas_estado=[cobertura],
              estudiante=NS(grupo=NS(director_id=usuario_id if rol == "director" else None)))
    monkeypatch.setattr(piars, "_cargar_piar_completo", AsyncMock(return_value=piar))
    db = NS(flush=AsyncMock())

    with pytest.raises(HTTPException) as error:
        await piars.update_estado_asignatura(
            uuid4(), asignatura_id,
            PiarAsignaturaEstadoUpdate(estado=estado, justificacion="Texto ajeno"),
            NS(id=usuario_id, rol=NS(es_directivo=rol == "directivo")), db,
        )
    assert error.value.status_code == 403
    assert cobertura.justificacion == "Justificación del docente"
    assert cobertura.estado == "no_requiere"
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["pendiente", "no_requiere"])
async def test_docente_asignado_resuelve_su_cobertura(monkeypatch, estado):
    docente_id, asignatura_id = uuid4(), uuid4()
    cobertura = NS(asignatura_id=asignatura_id, docente_id=docente_id,
                   estado="pendiente", justificacion=None)
    monkeypatch.setattr(piars, "_cargar_piar_completo", AsyncMock(return_value=NS(
        estado="borrador", asignaturas_estado=[cobertura],
    )))
    db = NS(flush=AsyncMock())
    resultado = await piars.update_estado_asignatura(
        uuid4(), asignatura_id,
        PiarAsignaturaEstadoUpdate(estado=estado, justificacion="  Logra los objetivos.  "),
        NS(id=docente_id, rol=NS(es_directivo=False)), db,
    )
    assert resultado.estado == estado
    assert resultado.justificacion == ("Logra los objetivos." if estado == "no_requiere" else None)
    db.flush.assert_awaited_once()


@pytest.mark.parametrize("rol", ["docente", "director", "directivo"])
def test_visibilidad_malla_segun_autoria_asignatura_y_direccion(rol):
    usuario = NS(id="teacher", rol=NS(es_directivo=rol == "directivo"))
    ajustes = [
        NS(id="propio", asignatura_id="math", area="Matemáticas", creado_por="teacher"),
        NS(id="autor_ajeno", asignatura_id="math", area="Matemáticas", creado_por="otro"),
        NS(id="asignatura_ajena", asignatura_id="art", area="Arte", creado_por="teacher"),
        NS(id="heredado", asignatura_id=None, area=" MATEMÁTICAS ", creado_por="teacher"),
    ]
    piar = NS(
        estudiante=NS(grupo=NS(director_id="teacher" if rol == "director" else "otro")),
        ajustes_razonables=ajustes,
        asignaturas_estado=[
            NS(asignatura_id="math", nombre_asignatura="Matemáticas", docente_id="teacher"),
            NS(asignatura_id="art", nombre_asignatura="Arte", docente_id="otro"),
        ],
    )
    visibles = piars._ajustes_visibles_para_usuario(piar, usuario)
    assert [a.id for a in visibles] == (
        [a.id for a in ajustes] if rol in ("director", "directivo") else ["propio", "heredado"]
    )
