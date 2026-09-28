# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Tests de seguridad del Setup Wizard (BOOTSTRAP_TOKEN).

Cubre:
- Una instalación ya configurada rechaza los tres endpoints de bootstrap.
- Una instalación nueva exige el header X-Bootstrap-Token.
- El servidor sin BOOTSTRAP_TOKEN configurado rechaza con 503.
- El token correcto permite continuar.
- El wiring de dependencias: solo GET /setup/status queda público.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.adapters.db.session import get_db
from app.core.config import get_settings
from app.entrypoints.api import middleware
from app.entrypoints.api.dependencies import require_bootstrap_token
from app.entrypoints.api.v1.endpoints import setup as setup_endpoints
from app.main import app

TOKEN = "token-de-instalacion-de-prueba"


# ---------------------------------------------------------------------------
# Fakes de base de datos
# ---------------------------------------------------------------------------

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
    def __init__(self, config=None):
        self._config = config

    async def execute(self, *args, **kwargs):
        return _Result(self._config)


class _FakeSessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


def _config(setup_completado: bool):
    if setup_completado:
        return SimpleNamespace(setup_completado=True)
    return None


@pytest.fixture
def cliente(monkeypatch):
    """Cliente HTTP con BD y settings simulados; limpia overrides al final."""
    def _crear(*, setup_completado: bool, bootstrap_token: str):
        config = _config(setup_completado)

        async def _fake_get_db():
            yield _FakeSession(config)

        app.dependency_overrides[get_db] = _fake_get_db
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
            BOOTSTRAP_TOKEN=bootstrap_token
        )
        monkeypatch.setattr(
            middleware,
            "AsyncSessionLocal",
            lambda: _FakeSessionCM(_FakeSession(config)),
        )
        return TestClient(app)

    yield _crear
    app.dependency_overrides.clear()


ENDPOINTS_BOOTSTRAP = [
    ("/api/v1/setup/test-db", {"user": "u", "password": "p", "database": "d"}),
    ("/api/v1/setup/configure", {}),
]


# ---------------------------------------------------------------------------
# Instalación configurada: rechazo permanente
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ruta,payload", ENDPOINTS_BOOTSTRAP)
def test_instalacion_configurada_rechaza_endpoints_json(cliente, ruta, payload):
    client = cliente(setup_completado=True, bootstrap_token=TOKEN)

    response = client.post(ruta, json=payload, headers={"X-Bootstrap-Token": TOKEN})

    assert response.status_code == 404


def test_instalacion_configurada_rechaza_upload_pei(cliente):
    client = cliente(setup_completado=True, bootstrap_token=TOKEN)

    response = client.post(
        "/api/v1/setup/upload-pei",
        data={"gemini_api_key": "x"},
        files={"file": ("pei.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"X-Bootstrap-Token": TOKEN},
    )

    assert response.status_code == 404


def test_instalacion_configurada_rechaza_sin_token(cliente):
    client = cliente(setup_completado=True, bootstrap_token=TOKEN)

    response = client.post("/api/v1/setup/configure", json={})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Instalación nueva: exigencia del token
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ruta,payload", ENDPOINTS_BOOTSTRAP)
def test_instalacion_nueva_sin_token_devuelve_401(cliente, ruta, payload):
    client = cliente(setup_completado=False, bootstrap_token=TOKEN)

    response = client.post(ruta, json=payload)

    assert response.status_code == 401


def test_instalacion_nueva_token_incorrecto_devuelve_401(cliente):
    client = cliente(setup_completado=False, bootstrap_token=TOKEN)

    response = client.post(
        "/api/v1/setup/test-db",
        json={"user": "u", "password": "p", "database": "d"},
        headers={"X-Bootstrap-Token": "otro-token"},
    )

    assert response.status_code == 401


def test_instalacion_nueva_sin_bootstrap_configurado_devuelve_503(cliente):
    client = cliente(setup_completado=False, bootstrap_token="")

    response = client.post(
        "/api/v1/setup/configure",
        json={},
        headers={"X-Bootstrap-Token": TOKEN},
    )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Dependencia: token correcto permite continuar
# ---------------------------------------------------------------------------

async def test_token_correcto_permite_continuar():
    await require_bootstrap_token(
        x_bootstrap_token=TOKEN,
        db=_FakeSession(None),
        settings=SimpleNamespace(BOOTSTRAP_TOKEN=TOKEN),
    )


async def test_dependencia_rechaza_sin_token_configurado():
    with pytest.raises(HTTPException) as exc:
        await require_bootstrap_token(
            x_bootstrap_token=TOKEN,
            db=_FakeSession(None),
            settings=SimpleNamespace(BOOTSTRAP_TOKEN=""),
        )

    assert exc.value.status_code == 503


async def test_dependencia_rechaza_token_incorrecto():
    with pytest.raises(HTTPException) as exc:
        await require_bootstrap_token(
            x_bootstrap_token="incorrecto",
            db=_FakeSession(None),
            settings=SimpleNamespace(BOOTSTRAP_TOKEN=TOKEN),
        )

    assert exc.value.status_code == 401


async def test_dependencia_invalida_token_al_completarse_setup():
    with pytest.raises(HTTPException) as exc:
        await require_bootstrap_token(
            x_bootstrap_token=TOKEN,
            db=_FakeSession(_config(True)),
            settings=SimpleNamespace(BOOTSTRAP_TOKEN=TOKEN),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Wiring: solo GET /setup/status queda sin token
# ---------------------------------------------------------------------------

def _dependencias_de(ruta: str):
    routes = {route.path: route for route in setup_endpoints.router.routes}
    return [dep.call for dep in routes[ruta].dependant.dependencies]


def test_endpoints_de_bootstrap_exigen_dependencia():
    for ruta in ("/setup/test-db", "/setup/configure", "/setup/upload-pei"):
        assert require_bootstrap_token in _dependencias_de(ruta), ruta


def test_status_no_exige_dependencia_de_bootstrap():
    assert require_bootstrap_token not in _dependencias_de("/setup/status")
