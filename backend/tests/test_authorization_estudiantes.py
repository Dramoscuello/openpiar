# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Tests de la política centralizada de autorización por estudiante."""

from datetime import date, datetime
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.adapters.db.models import CargaAcademicaORM, EstudianteORM, GrupoORM
from app.entrypoints.api import middleware
from app.entrypoints.api.authorization import (
    authorize_group_access,
    authorize_student_access,
    puede_acceder,
    subquery_grupos_con_acceso,
)
from app.entrypoints.api.dependencies import get_estudiante_repo, get_current_user
from app.main import app

ESTUDIANTE_ID = uuid4()
GRUPO_ID = uuid4()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

def _usuario(rol: str = "docente_aula", usuario_id=None):
    return NS(
        id=usuario_id or uuid4(),
        rol=NS(es_directivo=(rol == "directivo")),
    )


class _Scalars:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _Result:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return _Scalars(self._value)


class _FakeSession:
    def __init__(self, *, estudiante=None, grupo=None, carga=None):
        self._estudiante = estudiante
        self._grupo = grupo
        self._carga = carga

    async def get(self, model, pk):
        if model is EstudianteORM:
            return self._estudiante
        if model is GrupoORM:
            return self._grupo
        return None

    async def execute(self, *args, **kwargs):
        return _Result(self._carga)


class _FakeSessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


def _estudiante(grupo_id=GRUPO_ID):
    return NS(id=ESTUDIANTE_ID, grupo_id=grupo_id)


def _grupo(director_id=None):
    return NS(id=GRUPO_ID, director_id=director_id)


# ---------------------------------------------------------------------------
# Matriz pura
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "accion,es_directivo,es_director_grupo,tiene_carga,esperado",
    [
        ("read", True, False, False, True),
        ("write", True, False, False, True),
        ("medical_read", True, False, False, True),
        ("family_read", True, False, False, True),
        ("delete", True, False, False, True),
        ("read", False, True, False, True),
        ("write", False, True, False, True),
        ("medical_read", False, True, False, True),
        ("family_read", False, True, False, True),
        ("delete", False, True, False, False),
        ("read", False, False, True, True),
        ("medical_read", False, False, True, True),
        ("write", False, False, True, False),
        ("family_read", False, False, True, False),
        ("delete", False, False, True, False),
        ("read", False, False, False, False),
        ("write", False, False, False, False),
        ("medical_read", False, False, False, False),
        ("family_read", False, False, False, False),
        ("delete", False, False, False, False),
    ],
)
def test_matriz_de_permisos(
    accion, es_directivo, es_director_grupo, tiene_carga, esperado
):
    assert puede_acceder(
        accion,
        es_directivo=es_directivo,
        es_director_grupo=es_director_grupo,
        tiene_carga=tiene_carga,
    ) is esperado


def test_accion_desconocida_falla():
    with pytest.raises(ValueError):
        puede_acceder(
            "exportar",
            es_directivo=True,
            es_director_grupo=False,
            tiene_carga=False,
        )


# ---------------------------------------------------------------------------
# authorize_student_access — servicio
# ---------------------------------------------------------------------------

async def test_directivo_tiene_acceso_total():
    usuario = _usuario("directivo")
    db = _FakeSession(estudiante=_estudiante())

    resultado = await authorize_student_access(db, usuario, ESTUDIANTE_ID, "delete")

    assert resultado.grupo_id == GRUPO_ID


async def test_estudiante_inexistente_devuelve_404():
    usuario = _usuario("directivo")
    db = _FakeSession(estudiante=None)

    with pytest.raises(HTTPException) as exc:
        await authorize_student_access(db, usuario, ESTUDIANTE_ID, "read")

    assert exc.value.status_code == 404


async def test_director_de_su_grupo_puede_escribir():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=usuario.id),
        carga=None,
    )

    await authorize_student_access(db, usuario, ESTUDIANTE_ID, "write")


async def test_director_de_otro_grupo_no_puede_escribir():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=None,
    )

    with pytest.raises(HTTPException) as exc:
        await authorize_student_access(db, usuario, ESTUDIANTE_ID, "write")

    assert exc.value.status_code == 403


async def test_director_de_otro_grupo_no_puede_leer():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=None,
    )

    with pytest.raises(HTTPException) as exc:
        await authorize_student_access(db, usuario, ESTUDIANTE_ID, "read")

    assert exc.value.status_code == 403


async def test_docente_con_carga_puede_leer_y_ver_salud():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    await authorize_student_access(db, usuario, ESTUDIANTE_ID, "read")
    await authorize_student_access(db, usuario, ESTUDIANTE_ID, "medical_read")


async def test_docente_con_carga_no_puede_escribir_ni_ver_hogar():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    for accion in ("write", "family_read", "delete"):
        with pytest.raises(HTTPException) as exc:
            await authorize_student_access(db, usuario, ESTUDIANTE_ID, accion)
        assert exc.value.status_code == 403


async def test_docente_sin_carga_no_accede():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=None,
    )

    with pytest.raises(HTTPException) as exc:
        await authorize_student_access(db, usuario, ESTUDIANTE_ID, "read")

    assert exc.value.status_code == 403


async def test_estudiante_sin_grupo_solo_accesible_para_directivo():
    usuario = _usuario()
    db = _FakeSession(estudiante=_estudiante(grupo_id=None))

    with pytest.raises(HTTPException) as exc:
        await authorize_student_access(db, usuario, ESTUDIANTE_ID, "read")

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# authorize_group_access — creación
# ---------------------------------------------------------------------------

async def test_directivo_puede_crear_en_cualquier_grupo():
    usuario = _usuario("directivo")
    db = _FakeSession(grupo=_grupo(director_id=uuid4()))

    await authorize_group_access(db, usuario, GRUPO_ID, "write")


async def test_director_puede_crear_en_su_grupo():
    usuario = _usuario()
    db = _FakeSession(grupo=_grupo(director_id=usuario.id))

    await authorize_group_access(db, usuario, GRUPO_ID, "write")


async def test_docente_con_carga_no_puede_crear_estudiantes():
    usuario = _usuario()
    db = _FakeSession(grupo=_grupo(director_id=uuid4()), carga=NS(id=uuid4()))

    with pytest.raises(HTTPException) as exc:
        await authorize_group_access(db, usuario, GRUPO_ID, "write")

    assert exc.value.status_code == 403


async def test_grupo_inexistente_devuelve_422():
    usuario = _usuario("directivo")
    db = _FakeSession(grupo=None)

    with pytest.raises(HTTPException) as exc:
        await authorize_group_access(db, usuario, GRUPO_ID, "write")

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Subquery de grupos para listados
# ---------------------------------------------------------------------------

def test_subquery_sin_restriccion_para_directivo():
    assert subquery_grupos_con_acceso(_usuario("directivo")) is None


def test_subquery_para_docente():
    consulta = subquery_grupos_con_acceso(_usuario())

    assert consulta is not None
    assert "carga_academica" in str(consulta)


# ---------------------------------------------------------------------------
# Endpoint: GET /estudiantes/{id}
# ---------------------------------------------------------------------------

def _estudiante_orm_falso():
    return NS(
        id=ESTUDIANTE_ID,
        nombres="Ana",
        apellidos="Pérez",
        tipo_documento="TI",
        numero_documento="123456",
        fecha_nacimiento=date(2015, 1, 1),
        departamento_residencia=None,
        municipio_residencia=None,
        direccion=None,
        barrio_vereda=None,
        lugar_nacimiento=None,
        telefono=None,
        correo=None,
        en_centro_proteccion=False,
        centro_proteccion_donde=None,
        pertenece_grupo_etnico=False,
        grupo_etnico=None,
        victima_conflicto=False,
        registro_victima=None,
        grupo_id=None,
        created_at=datetime(2025, 1, 1),
    )


class _RepoFalso:
    def __init__(self, estudiante):
        self._estudiante = estudiante
        self._session = NS()

    async def find_by_id(self, estudiante_id):
        return self._estudiante


@pytest.fixture
def cliente(monkeypatch):
    def _crear(usuario, estudiante):
        app.dependency_overrides[get_current_user] = lambda: usuario
        app.dependency_overrides[get_estudiante_repo] = lambda: _RepoFalso(estudiante)
        monkeypatch.setattr(
            middleware,
            "AsyncSessionLocal",
            lambda: _FakeSessionCM(
                _FakeSession(carga=NS(setup_completado=True))
            ),
        )
        return TestClient(app)

    yield _crear
    app.dependency_overrides.clear()


def test_endpoint_rechaza_docente_ajeno(cliente):
    client = cliente(_usuario(), _estudiante_orm_falso())

    response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}")

    assert response.status_code == 403


def test_endpoint_permite_directivo(cliente):
    client = cliente(_usuario("directivo"), _estudiante_orm_falso())

    response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(ESTUDIANTE_ID)
