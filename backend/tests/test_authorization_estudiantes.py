# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Tests de la política centralizada de autorización por estudiante."""

import logging
from datetime import date, datetime
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.adapters.db.models import CargaAcademicaORM, EstudianteORM, GrupoORM
from app.adapters.db.session import get_db
from app.entrypoints.api import middleware
from app.entrypoints.api.authorization import (
    authorize_group_access,
    authorize_student_access,
    puede_acceder,
    subquery_grupos_con_acceso,
)
from app.entrypoints.api.dependencies import get_estudiante_repo, get_current_user
from app.entrypoints.api.schemas import (
    EntornoHogarRequest,
    EntornoSaludRequest,
    TrayectoriaEducativaRequest,
)
from app.entrypoints.api.v1.endpoints import piars
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
    def __init__(self, *, estudiante=None, grupo=None, carga=None, resultados=None):
        self._estudiante = estudiante
        self._grupo = grupo
        self._carga = carga
        self._resultados = list(resultados or [])
        self.eliminado = None
        self.confirmado = False
        self.agregado = None

    async def get(self, model, pk):
        if model is EstudianteORM:
            return self._estudiante
        if model is GrupoORM:
            return self._grupo
        return None

    async def execute(self, *args, **kwargs):
        if self._resultados:
            return _Result(self._resultados.pop(0))
        return _Result(self._carga)

    def add(self, obj):
        self.agregado = obj

    async def flush(self):
        if self.agregado is not None and getattr(self.agregado, "id", None) is None:
            self.agregado.id = uuid4()

    async def refresh(self, obj):
        return None

    async def delete(self, obj):
        self.eliminado = obj

    async def commit(self):
        self.confirmado = True


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
        ("delete", False, True, False, True),
        ("read", False, False, True, True),
        ("medical_read", False, False, True, True),
        ("family_read", False, False, True, True),
        ("write", False, False, True, False),
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


async def test_director_de_su_grupo_puede_eliminar():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=usuario.id),
        carga=None,
    )

    await authorize_student_access(db, usuario, ESTUDIANTE_ID, "delete")


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


async def test_docente_con_carga_puede_ver_hogar():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    await authorize_student_access(db, usuario, ESTUDIANTE_ID, "family_read")


async def test_docente_con_carga_no_puede_escribir_ni_eliminar():
    usuario = _usuario()
    db = _FakeSession(
        estudiante=_estudiante(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    for accion in ("write", "delete"):
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
    def _crear(usuario, estudiante, *, grupo=None, carga=None, resultados=None):
        async def _fake_get_db():
            yield _FakeSession(
                estudiante=estudiante,
                grupo=grupo,
                carga=carga,
                resultados=resultados,
            )

        app.dependency_overrides[get_current_user] = lambda: usuario
        app.dependency_overrides[get_estudiante_repo] = lambda: _RepoFalso(estudiante)
        app.dependency_overrides[get_db] = _fake_get_db
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


def test_endpoint_permite_eliminar_al_director_del_grupo(cliente):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    client = cliente(usuario, estudiante, grupo=_grupo(director_id=usuario.id))

    response = client.delete(f"/api/v1/estudiantes/{ESTUDIANTE_ID}")

    assert response.status_code == 204


def test_endpoint_rechaza_eliminar_a_docente_con_carga(cliente):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    response = client.delete(f"/api/v1/estudiantes/{ESTUDIANTE_ID}")

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Endpoint: GET /piars/{piar_id}/pdf
# ---------------------------------------------------------------------------

def _piar_falso():
    return NS(
        estudiante_id=ESTUDIANTE_ID,
        estudiante=NS(
            nombres="Ana",
            apellidos="Pérez",
            numero_documento="123456",
        ),
    )


def test_endpoint_pdf_rechaza_usuario_ajeno(cliente, monkeypatch):
    async def _cargar(db, piar_id):
        return _piar_falso()

    monkeypatch.setattr(piars, "_cargar_piar_completo", _cargar)
    client = cliente(_usuario(), _estudiante_orm_falso())

    response = client.get(f"/api/v1/piars/{uuid4()}/pdf")

    assert response.status_code == 403


def test_endpoint_pdf_permite_docente_con_carga(cliente, monkeypatch):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID

    async def _cargar(db, piar_id):
        return _piar_falso()

    async def _resolver(db, piar, periodo_id):
        return None

    def _completitud(piar, periodo_id):
        return NS(secciones=[])

    async def _generar(db, piar, modo, faltantes, periodo):
        return b"%PDF-1.4 prueba"

    monkeypatch.setattr(piars, "_cargar_piar_completo", _cargar)
    monkeypatch.setattr(piars, "_resolver_periodo", _resolver)
    monkeypatch.setattr(piars, "_evaluar_completitud", _completitud)
    monkeypatch.setattr(piars, "_generar_pdf_actual", _generar)
    monkeypatch.setattr(piars, "nombre_archivo_piar", lambda nombre, apellido: "piar.pdf")

    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    response = client.get(f"/api/v1/piars/{uuid4()}/pdf")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 prueba"


# ---------------------------------------------------------------------------
# Auditoría por logs de accesos a información médica
# ---------------------------------------------------------------------------

def _registros_auditoria(caplog, recurso: str) -> list:
    return [
        registro.getMessage()
        for registro in caplog.records
        if "acceso_sensible" in registro.getMessage()
        and f"recurso={recurso}" in registro.getMessage()
    ]


def test_endpoint_salud_audita_lectura(cliente, caplog):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    salud = NS(
        **EntornoSaludRequest().model_dump(),
        id=uuid4(),
        estudiante_id=ESTUDIANTE_ID,
    )
    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        resultados=[NS(id=uuid4()), salud],
    )

    with caplog.at_level(logging.INFO, logger="app.audit"):
        response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/salud")

    assert response.status_code == 200
    registros = _registros_auditoria(caplog, "salud")
    assert len(registros) == 1
    assert "accion=leer" in registros[0]
    assert str(usuario.id) in registros[0]
    assert str(ESTUDIANTE_ID) in registros[0]
    assert "diagnostico" not in registros[0]


def test_endpoint_salud_no_audita_ajeno(cliente, caplog):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        resultados=[None],
    )

    with caplog.at_level(logging.INFO, logger="app.audit"):
        response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/salud")

    assert response.status_code == 403
    assert _registros_auditoria(caplog, "salud") == []


def test_endpoint_descarga_soporte_permite_y_audita(cliente, caplog):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    salud = NS(
        soporte_medico_archivo=b"%PDF-1.4 soporte",
        soporte_medico_nombre="soporte.pdf",
    )
    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        resultados=[NS(id=uuid4()), salud],
    )

    with caplog.at_level(logging.INFO, logger="app.audit"):
        response = client.get(
            f"/api/v1/estudiantes/{ESTUDIANTE_ID}/salud/soporte"
        )

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 soporte"
    registros = _registros_auditoria(caplog, "soporte_medico")
    assert len(registros) == 1
    assert "accion=descargar" in registros[0]
    assert str(usuario.id) in registros[0]


def test_endpoint_descarga_soporte_rechaza_ajeno_sin_auditar(cliente, caplog):
    usuario = _usuario()
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    client = cliente(
        usuario,
        estudiante,
        grupo=_grupo(director_id=uuid4()),
        resultados=[None],
    )

    with caplog.at_level(logging.INFO, logger="app.audit"):
        response = client.get(
            f"/api/v1/estudiantes/{ESTUDIANTE_ID}/salud/soporte"
        )

    assert response.status_code == 403
    assert _registros_auditoria(caplog, "soporte_medico") == []


def test_auditoria_sanitiza_ip_y_user_agent(caplog):
    from starlette.requests import Request as StarletteRequest

    from app.core.audit import registrar_acceso_sensible

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"x-forwarded-for", b"1.1.1.1, 2.2.2.2"),
            (b"user-agent", b"Agente\r\nmalicioso"),
        ],
        "client": ("10.0.0.5", 1234),
    }
    request = StarletteRequest(scope)

    with caplog.at_level(logging.INFO, logger="app.audit"):
        registrar_acceso_sensible(
            request,
            usuario_id="usuario-1",
            estudiante_id="estudiante-1",
            recurso="salud",
            accion="leer",
        )

    mensaje = _registros_auditoria(caplog, "salud")[0]
    assert "ip=1.1.1.1" in mensaje
    assert "AgenteX" in mensaje or "Agentemalicioso" in mensaje
    assert "\n" not in mensaje
    assert "\r" not in mensaje


# ---------------------------------------------------------------------------
# Endpoints: hogar y trayectoria (acceso cruzado y solo lectura)
# ---------------------------------------------------------------------------

def _hogar_falso(**overrides):
    datos = EntornoHogarRequest().model_dump()
    datos.update(overrides)
    return NS(**datos, id=uuid4(), estudiante_id=ESTUDIANTE_ID)


def _trayectoria_falsa(**overrides):
    datos = TrayectoriaEducativaRequest().model_dump()
    datos.update(overrides)
    return NS(**datos, id=uuid4(), estudiante_id=ESTUDIANTE_ID)


def _estudiante_con_grupo():
    estudiante = _estudiante_orm_falso()
    estudiante.grupo_id = GRUPO_ID
    return estudiante


def test_endpoint_hogar_rechaza_ajeno(cliente):
    client = cliente(_usuario(), _estudiante_con_grupo(), grupo=_grupo(director_id=uuid4()))

    assert client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar").status_code == 403
    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={}).status_code == 403
    assert client.patch(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={}).status_code == 403


def test_endpoint_hogar_docente_con_carga_lee_todo(cliente):
    hogar = _hogar_falso(nombre_madre="Madre", telefono_madre="3001234567")
    client = cliente(
        _usuario(),
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=uuid4()),
        resultados=[NS(id=uuid4()), hogar],
    )

    response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar")

    assert response.status_code == 200
    body = response.json()
    assert body["nombre_madre"] == "Madre"
    assert body["telefono_madre"] == "3001234567"


def test_endpoint_hogar_docente_con_carga_no_escribe(cliente):
    client = cliente(
        _usuario(),
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={}).status_code == 403
    assert client.patch(
        f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={"nombre_madre": "X"}
    ).status_code == 403


def test_endpoint_hogar_director_crea_y_actualiza(cliente):
    usuario = _usuario()
    client = cliente(
        usuario,
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=usuario.id),
        resultados=[None],
    )
    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={}).status_code == 201

    hogar = _hogar_falso()
    client = cliente(
        usuario,
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=usuario.id),
        resultados=[None, hogar],
    )
    response = client.patch(
        f"/api/v1/estudiantes/{ESTUDIANTE_ID}/hogar", json={"nombre_madre": "Madre"}
    )
    assert response.status_code == 200
    assert response.json()["nombre_madre"] == "Madre"


def test_endpoint_trayectoria_rechaza_ajeno(cliente):
    client = cliente(_usuario(), _estudiante_con_grupo(), grupo=_grupo(director_id=uuid4()))

    assert client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria").status_code == 403
    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={}).status_code == 403
    assert client.patch(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={}).status_code == 403


def test_endpoint_trayectoria_docente_con_carga_lee(cliente):
    trayectoria = _trayectoria_falsa(ultimo_grado_cursado="5°")
    client = cliente(
        _usuario(),
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=uuid4()),
        resultados=[NS(id=uuid4()), trayectoria],
    )

    response = client.get(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria")

    assert response.status_code == 200
    assert response.json()["ultimo_grado_cursado"] == "5°"


def test_endpoint_trayectoria_docente_con_carga_no_escribe(cliente):
    client = cliente(
        _usuario(),
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=uuid4()),
        carga=NS(id=uuid4()),
    )

    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={}).status_code == 403
    assert client.patch(
        f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={"ultimo_grado_cursado": "X"}
    ).status_code == 403


def test_endpoint_trayectoria_director_crea_y_actualiza(cliente):
    usuario = _usuario()
    client = cliente(
        usuario,
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=usuario.id),
        resultados=[None],
    )
    assert client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={}).status_code == 201

    trayectoria = _trayectoria_falsa()
    client = cliente(
        usuario,
        _estudiante_con_grupo(),
        grupo=_grupo(director_id=usuario.id),
        resultados=[None, trayectoria],
    )
    response = client.patch(
        f"/api/v1/estudiantes/{ESTUDIANTE_ID}/trayectoria", json={"ultimo_grado_cursado": "5°"}
    )
    assert response.status_code == 200
    assert response.json()["ultimo_grado_cursado"] == "5°"
