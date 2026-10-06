# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Pruebas de la política centralizada de autorización de PIAR."""

from types import SimpleNamespace as NS
from uuid import uuid4
import re

import pytest
from fastapi import HTTPException

from app.adapters.db.models import EstudianteORM, GrupoORM, PiarORM
from app.entrypoints.api.authorization import (
    authorize_piar_access,
    puede_acceder_piar,
)
from app.entrypoints.api.schemas import PiarResponse
from app.entrypoints.api.v1.endpoints import piars

PIAR_ID = uuid4()
ESTUDIANTE_ID = uuid4()
GRUPO_ID = uuid4()


def _usuario(usuario_id=None, *, directivo=False):
    return NS(id=usuario_id or uuid4(), rol=NS(es_directivo=directivo))


def _piar(*, director_id=None, docentes=None):
    grupo = NS(
        id=GRUPO_ID,
        director_id=director_id,
        carga=[NS(docente_id=docente_id) for docente_id in (docentes or [])],
    )
    estudiante = NS(id=ESTUDIANTE_ID, grupo_id=GRUPO_ID, grupo=grupo)
    return NS(id=PIAR_ID, estudiante_id=ESTUDIANTE_ID, estudiante=estudiante)


def _cobertura(docente_id):
    return NS(docente_id=docente_id)


@pytest.mark.parametrize(
    "accion,es_directivo,es_director,tiene_carga,es_docente_asignado,esperado",
    [
        ("read", True, False, False, False, True),
        ("read", False, True, False, False, True),
        ("read", False, False, True, False, True),
        ("edit", True, False, False, False, True),
        ("edit", False, True, False, False, True),
        ("edit", False, False, True, False, False),
        ("sign", False, False, True, False, False),
        ("audit_read", False, True, False, False, True),
        ("export", False, False, True, False, True),
        ("adjustments", False, False, True, True, True),
        ("adjustments", True, False, False, False, False),
        ("adjustments", False, False, True, False, False),
        ("ai_generate", True, False, False, False, True),
        ("ai_generate", False, False, True, True, True),
        ("ai_generate", False, True, False, False, False),
        ("ai_generate", False, False, True, False, False),
    ],
)
def test_matriz_piar(
    accion,
    es_directivo,
    es_director,
    tiene_carga,
    es_docente_asignado,
    esperado,
):
    assert puede_acceder_piar(
        accion,
        es_directivo=es_directivo,
        es_director_grupo=es_director,
        tiene_carga=tiene_carga,
        es_docente_asignado=es_docente_asignado,
    ) is esperado


def test_accion_piar_desconocida_falla():
    with pytest.raises(ValueError):
        puede_acceder_piar(
            "delete",
            es_directivo=True,
            es_director_grupo=False,
            tiene_carga=False,
        )


async def test_directivo_tiene_acceso_institucional_al_piar():
    usuario = _usuario(directivo=True)
    piar = _piar()

    for accion in ("read", "edit", "evidences", "sign", "export", "audit_read"):
        assert await authorize_piar_access(
            NS(), usuario, PIAR_ID, accion, piar=piar
        ) is piar


async def test_director_del_grupo_puede_editar_y_auditar():
    usuario = _usuario()
    piar = _piar(director_id=usuario.id)

    for accion in ("read", "edit", "sign", "export", "audit_read"):
        await authorize_piar_access(NS(), usuario, PIAR_ID, accion, piar=piar)


async def test_director_de_otro_grupo_no_accede_al_piar():
    usuario = _usuario()
    piar = _piar(director_id=uuid4())

    for accion in ("read", "edit", "evidences", "sign", "export", "audit_read"):
        with pytest.raises(HTTPException) as error:
            await authorize_piar_access(NS(), usuario, PIAR_ID, accion, piar=piar)
        assert error.value.status_code == 403


async def test_docente_con_carga_solo_tiene_lectura_del_piar():
    usuario = _usuario()
    piar = _piar(director_id=uuid4(), docentes=[usuario.id])

    for accion in ("read", "evidences", "export"):
        await authorize_piar_access(NS(), usuario, PIAR_ID, accion, piar=piar)

    for accion in ("edit", "sign", "audit_read"):
        with pytest.raises(HTTPException) as error:
            await authorize_piar_access(NS(), usuario, PIAR_ID, accion, piar=piar)
        assert error.value.status_code == 403


async def test_solo_docente_asignado_puede_modificar_ajustes():
    usuario = _usuario()
    piar = _piar(director_id=uuid4(), docentes=[usuario.id])

    await authorize_piar_access(
        NS(), usuario, PIAR_ID, "adjustments", piar=piar,
        cobertura=_cobertura(usuario.id),
    )

    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            NS(), usuario, PIAR_ID, "adjustments", piar=piar,
            cobertura=_cobertura(uuid4()),
        )
    assert error.value.status_code == 403


class _ResultadoConValor:
    def __init__(self, valor):
        self._valor = valor

    def scalars(self):
        return self

    def first(self):
        return self._valor


class _DbConCarga:
    """Fake DB: execute() responde si existe carga del docente en la asignatura."""

    def __init__(self, valor):
        self._valor = valor

    async def execute(self, *args, **kwargs):
        return _ResultadoConValor(self._valor)


class _DbPeriodos:
    """Fake DB: get() no encuentra el periodo, execute() devuelve uno activo."""

    def __init__(self, periodo):
        self._periodo = periodo

    async def get(self, _model, _pk):
        return None

    async def execute(self, *args, **kwargs):
        return _ResultadoConValor(self._periodo)


async def test_director_de_grupo_no_genera_ia_sin_impartir_la_asignatura():
    usuario = _usuario()
    piar = _piar(director_id=usuario.id)

    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            _DbConCarga(None), usuario, PIAR_ID, "ai_generate",
            piar=piar, cobertura=None,
        )
    assert error.value.status_code == 403


async def test_docente_asignado_genera_ia():
    usuario = _usuario()
    piar = _piar(director_id=uuid4())
    cobertura = NS(docente_id=usuario.id, asignatura_id=uuid4())

    await authorize_piar_access(
        NS(), usuario, PIAR_ID, "ai_generate", piar=piar, cobertura=cobertura
    )


async def test_docente_con_carga_actual_genera_ia_aunque_la_cobertura_sea_ajena():
    usuario = _usuario()
    piar = _piar(director_id=uuid4())
    cobertura = NS(docente_id=uuid4(), asignatura_id=uuid4())

    await authorize_piar_access(
        _DbConCarga(NS(id=uuid4())), usuario, PIAR_ID, "ai_generate",
        piar=piar, cobertura=cobertura,
    )


async def test_docente_sin_carga_ni_cobertura_no_genera_ia():
    usuario = _usuario()
    piar = _piar(director_id=uuid4())
    cobertura = NS(docente_id=uuid4(), asignatura_id=uuid4())

    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            _DbConCarga(None), usuario, PIAR_ID, "ai_generate",
            piar=piar, cobertura=cobertura,
        )
    assert error.value.status_code == 403


async def test_generacion_ia_resuelve_cobertura_por_asignatura_id():
    usuario = _usuario()
    asignatura_id = uuid4()
    cobertura = NS(
        docente_id=usuario.id,
        asignatura_id=asignatura_id,
        nombre_asignatura="Matemáticas",
        periodo_id=1,
    )
    piar = _piar(director_id=uuid4())
    piar.asignaturas_estado = [cobertura]
    data = NS(area="Área desactualizada", asignatura_id=asignatura_id, periodo_id=1)

    await piars._autorizar_generacion_ia(
        _DbPeriodos(NS(id=1)), usuario, PIAR_ID, piar, data
    )


async def test_generacion_ia_cae_a_cobertura_propia_si_el_area_no_coincide():
    usuario = _usuario()
    cobertura = NS(
        docente_id=usuario.id,
        asignatura_id=uuid4(),
        nombre_asignatura="Matemáticas",
        periodo_id=1,
    )
    piar = _piar(director_id=uuid4())
    piar.asignaturas_estado = [cobertura]
    data = NS(area="Área inexistente", asignatura_id=None, periodo_id=None)

    await piars._autorizar_generacion_ia(
        _DbPeriodos(NS(id=1)), usuario, PIAR_ID, piar, data
    )


async def test_la_autoria_no_sustituye_el_acceso_al_piar():
    usuario = _usuario()
    piar = _piar(director_id=uuid4())

    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            NS(), usuario, PIAR_ID, "evidences", piar=piar,
            propietario_id=usuario.id,
        )
    assert error.value.status_code == 403


async def test_un_recurso_sin_autor_no_se_considera_propiedad_del_usuario():
    usuario = _usuario()
    piar = _piar(director_id=usuario.id)

    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            NS(), usuario, PIAR_ID, "evidences", piar=piar,
            propietario_id=None,
        )
    assert error.value.status_code == 403


class _Result:
    def scalars(self):
        return self

    def first(self):
        return None


class _DbSinPiar:
    async def execute(self, *args, **kwargs):
        return _Result()


async def test_piar_inexistente_devuelve_404():
    with pytest.raises(HTTPException) as error:
        await authorize_piar_access(
            _DbSinPiar(), _usuario(), PIAR_ID, "read"
        )
    assert error.value.status_code == 404


class _DbAccesoEstudiante:
    def __init__(self, estudiante, grupo):
        self.estudiante = estudiante
        self.grupo = grupo
        self.execute_calls = 0

    async def get(self, model, _pk):
        if model is EstudianteORM:
            return self.estudiante
        if model is GrupoORM:
            return self.grupo
        return None

    async def execute(self, *args, **kwargs):
        self.execute_calls += 1
        return _Result()


async def test_get_piar_rechaza_grupo_ajeno_antes_de_cargar_relaciones():
    usuario = _usuario()
    estudiante = NS(id=ESTUDIANTE_ID, grupo_id=GRUPO_ID)
    grupo = NS(id=GRUPO_ID, director_id=uuid4(), carga=[])
    db = _DbAccesoEstudiante(estudiante, grupo)

    with pytest.raises(HTTPException) as error:
        await piars.get_piar_by_estudiante(
            ESTUDIANTE_ID, usuario, None, None, db
        )

    assert error.value.status_code == 403
    # Solo se ejecutó la consulta de carga usada por la autorización; la
    # consulta que carga el PIAR y sus relaciones nunca se ejecutó.
    assert db.execute_calls == 1


async def test_exportar_historial_rechaza_grupo_ajeno():
    usuario = _usuario()
    grupo = NS(id=GRUPO_ID, director_id=uuid4(), carga=[])
    piar = NS(
        id=PIAR_ID,
        estudiante_id=ESTUDIANTE_ID,
        estudiante=NS(id=ESTUDIANTE_ID, grupo_id=GRUPO_ID, grupo=grupo),
    )

    class _Db:
        async def get(self, model, _pk):
            return piar if model is PiarORM else None

        async def execute(self, *args, **kwargs):
            raise AssertionError("No debe consultar la auditoría sin autorización")

    with pytest.raises(HTTPException) as error:
        await piars.export_historial_pdf(PIAR_ID, usuario, _Db())

    assert error.value.status_code == 403


def test_respuesta_piar_no_expone_relaciones_del_estudiante():
    campos = PiarResponse.model_fields

    assert "estudiante" not in campos
    assert "entorno_salud" not in campos
    assert "entorno_hogar" not in campos
    assert "numero_documento" not in campos


def test_nombre_de_auditoria_no_incluye_documento():
    nombre = piars._nombre_archivo_auditoria(
        NS(nombres="María José", apellidos="Pérez Gómez", numero_documento="123456789")
    )

    assert re.fullmatch(r"Auditoria_PIAR_Maria_Jose_Perez_Gomez_[A-Z0-9]{6}\.pdf", nombre)
    assert "123456789" not in nombre
