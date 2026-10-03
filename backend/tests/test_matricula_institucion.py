# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""La institución de la matrícula se toma de la configuración, no del cliente."""

from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.adapters.db.models import EstudianteORM
from app.adapters.db.session import get_db
from app.entrypoints.api import middleware
from app.entrypoints.api.dependencies import get_current_user
from app.main import app

ESTUDIANTE_ID = uuid4()
NOMBRE_CONFIGURADO = "Colegio Configurado"

PAYLOAD = {
    "institucion_educativa": "Institución Escrita a Mano",
    "sede": "Sede Principal",
    "grado_ingreso": "6° - 6-A",
    "jornada": "unica",
}


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
    def __init__(self, *, resultados=None):
        self._resultados = list(resultados or [])
        self.agregado = None

    async def get(self, model, pk):
        if model is EstudianteORM:
            return NS(id=ESTUDIANTE_ID, grupo_id=None)
        return None

    async def execute(self, *args, **kwargs):
        return _Result(self._resultados.pop(0) if self._resultados else None)

    def add(self, obj):
        self.agregado = obj

    async def flush(self):
        if self.agregado is not None and getattr(self.agregado, "id", None) is None:
            self.agregado.id = uuid4()

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None


class _FakeSessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


def _configuracion():
    return NS(nombre_institucion=NOMBRE_CONFIGURADO)


@pytest.fixture
def cliente(monkeypatch):
    def _crear(resultados):
        async def _fake_get_db():
            yield _FakeSession(resultados=resultados)

        app.dependency_overrides[get_current_user] = lambda: NS(
            id=uuid4(), rol=NS(es_directivo=True)
        )
        app.dependency_overrides[get_db] = _fake_get_db
        monkeypatch.setattr(
            middleware,
            "AsyncSessionLocal",
            lambda: _FakeSessionCM(_FakeSession(resultados=[NS(setup_completado=True)])),
        )
        return TestClient(app)

    yield _crear
    app.dependency_overrides.clear()


def test_crear_matricula_ignora_el_nombre_del_cliente(cliente):
    client = cliente([_configuracion()])

    response = client.post(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/matricula", json=PAYLOAD)

    assert response.status_code == 201
    assert response.json()["institucion_educativa"] == NOMBRE_CONFIGURADO


def test_actualizar_matricula_ignora_el_nombre_del_cliente(cliente):
    matricula = NS(
        id=uuid4(),
        estudiante_id=ESTUDIANTE_ID,
        institucion_educativa="Otro Nombre",
        sede="Sede Principal",
        grado_ingreso="6° - 6-A",
        jornada="unica",
        medio_transporte=None,
        distancia_tiempo_hogar=None,
    )
    client = cliente([matricula, _configuracion()])

    response = client.patch(f"/api/v1/estudiantes/{ESTUDIANTE_ID}/matricula", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json()["institucion_educativa"] == NOMBRE_CONFIGURADO
    assert matricula.institucion_educativa == NOMBRE_CONFIGURADO
