# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Tests anti-SSRF del endpoint POST /setup/test-db.

Verifica que el endpoint:
- No acepte host, puerto ni credenciales desde el cliente.
- Pruebe exclusivamente el PostgreSQL configurado en el servidor.
- Use un timeout corto.
- No exponga excepciones internas de SQLAlchemy/asyncpg.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.adapters.db.session import get_db
from app.core.config import get_settings
from app.entrypoints.api import middleware
from app.entrypoints.api.v1.endpoints import setup as setup_endpoints
from app.main import app

TOKEN = "token-de-instalacion-de-prueba"
CONFIGURED_URL = "postgresql+asyncpg://openpiar_user:secreto@db:5432/openpiar_db"


# ---------------------------------------------------------------------------
# Fakes
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


class _FakeConnection:
    def __init__(self, delay: float = 0, error: Exception | None = None):
        self._delay = delay
        self._error = error

    async def __aenter__(self):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        return None


class _FakeEngine:
    def __init__(self, connection: _FakeConnection):
        self._connection = connection

    def connect(self):
        return self._connection

    async def dispose(self):
        return None


def _settings_falsos() -> SimpleNamespace:
    return SimpleNamespace(
        DATABASE_URL=CONFIGURED_URL,
        DB_HOST="db",
        DB_PORT=5432,
        DB_NAME="openpiar_db",
    )


@pytest.fixture
def cliente(monkeypatch):
    """Cliente HTTP con BD simulada, settings y factory de engine capturados."""
    config = None

    async def _fake_get_db():
        yield _FakeSession(config)

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        BOOTSTRAP_TOKEN=TOKEN
    )
    monkeypatch.setattr(
        middleware,
        "AsyncSessionLocal",
        lambda: _FakeSessionCM(_FakeSession(config)),
    )

    capturado: dict = {}

    def _factory(url, **kwargs):
        capturado["url"] = url
        capturado["kwargs"] = kwargs
        return _FakeEngine(_FakeConnection())

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())

    yield TestClient(app), capturado
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Contrato: sin body controlable por el cliente
# ---------------------------------------------------------------------------

def test_route_no_declara_body():
    routes = {route.path: route for route in setup_endpoints.router.routes}
    assert routes["/setup/test-db"].dependant.body_params == []


def test_openapi_no_expone_request_body():
    operacion = app.openapi()["paths"]["/api/v1/setup/test-db"]["post"]
    assert "requestBody" not in operacion


# ---------------------------------------------------------------------------
# SSRF: hosts y puertos del cliente se ignoran
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("host", ["127.0.0.1", "169.254.169.254", "10.0.0.1"])
@pytest.mark.parametrize("puerto", [22, 80, 5432, 6379])
def test_ignora_host_y_puerto_del_cliente(cliente, host, puerto):
    client, capturado = cliente

    response = client.post(
        "/api/v1/setup/test-db",
        json={"host": host, "port": puerto, "user": "x", "password": "y", "database": "z"},
        headers={"X-Bootstrap-Token": TOKEN},
    )

    assert response.status_code == 200
    assert capturado["url"] == CONFIGURED_URL


# ---------------------------------------------------------------------------
# Timeout y saneamiento de errores
# ---------------------------------------------------------------------------

async def test_timeout_corto_configurado(monkeypatch):
    capturado: dict = {}

    def _factory(url, **kwargs):
        capturado["kwargs"] = kwargs
        return _FakeEngine(_FakeConnection())

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())

    await setup_endpoints.test_database_connection()

    assert capturado["kwargs"]["connect_args"]["timeout"] <= 5


async def test_exito_devuelve_mensaje(monkeypatch):
    def _factory(url, **kwargs):
        return _FakeEngine(_FakeConnection())

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())

    response = await setup_endpoints.test_database_connection()

    assert response.success is True
    assert "exitosa" in response.message


async def test_fallo_no_expone_excepcion_interna(monkeypatch):
    secreto = "postgresql://openpiar_user:clave-supersecreta@10.0.0.1/db"

    def _factory(url, **kwargs):
        return _FakeEngine(_FakeConnection(error=RuntimeError(f"detalle: {secreto}")))

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())

    response = await setup_endpoints.test_database_connection()

    assert response.success is False
    assert secreto not in response.message
    assert "clave-supersecreta" not in response.message
    assert "RuntimeError" not in response.message


async def test_timeout_devuelve_mensaje_generico(monkeypatch):
    def _factory(url, **kwargs):
        return _FakeEngine(_FakeConnection(delay=5))

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())
    monkeypatch.setattr(setup_endpoints, "TIMEOUT_CONEXION_SEGUNDOS", 0.05)

    response = await asyncio.wait_for(
        setup_endpoints.test_database_connection(), timeout=2
    )

    assert response.success is False
    assert "tiempo de espera" in response.message.lower()


# ---------------------------------------------------------------------------
# BD caída: la dependencia tolera no poder verificar el estado
# ---------------------------------------------------------------------------

def test_estado_no_verificable_permite_diagnostico(monkeypatch):
    class _DBRota:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("bd caída")

    async def _fake_get_db():
        yield _DBRota()

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        BOOTSTRAP_TOKEN=TOKEN
    )
    monkeypatch.setattr(setup_endpoints, "settings", _settings_falsos())

    def _factory(url, **kwargs):
        return _FakeEngine(_FakeConnection(error=RuntimeError("no conecta")))

    monkeypatch.setattr(setup_endpoints, "create_async_engine", _factory)

    try:
        response = TestClient(app).post(
            "/api/v1/setup/test-db", headers={"X-Bootstrap-Token": TOKEN}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "logs del servidor" in body["message"]
