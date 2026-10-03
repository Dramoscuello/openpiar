# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Tests de la carga académica por docente (reemplazo en lote)."""

from uuid import uuid4

from app.entrypoints.api.v1.endpoints.gestion_escolar import calcular_cambios_carga
from app.main import app

A, B, C = uuid4(), uuid4(), uuid4()
G1, G2, G3 = uuid4(), uuid4(), uuid4()


def test_sin_cambios():
    actuales = {(A, G1), (B, G2)}
    deseadas = {(A, G1), (B, G2)}

    eliminar, crear = calcular_cambios_carga(actuales, deseadas)

    assert eliminar == set()
    assert crear == set()


def test_solo_altas():
    actuales = {(A, G1)}
    deseadas = {(A, G1), (A, G2), (B, G1)}

    eliminar, crear = calcular_cambios_carga(actuales, deseadas)

    assert eliminar == set()
    assert crear == {(A, G2), (B, G1)}


def test_solo_bajas():
    actuales = {(A, G1), (A, G2), (B, G1)}
    deseadas = {(A, G1)}

    eliminar, crear = calcular_cambios_carga(actuales, deseadas)

    assert eliminar == {(A, G2), (B, G1)}
    assert crear == set()


def test_mixto():
    actuales = {(A, G1), (A, G2), (B, G1)}
    deseadas = {(A, G1), (B, G2), (C, G3)}

    eliminar, crear = calcular_cambios_carga(actuales, deseadas)

    assert eliminar == {(A, G2), (B, G1)}
    assert crear == {(B, G2), (C, G3)}


def test_vaciar_toda_la_carga():
    actuales = {(A, G1), (B, G2)}

    eliminar, crear = calcular_cambios_carga(actuales, set())

    assert eliminar == actuales
    assert crear == set()


def test_contrato_openapi_del_endpoint_por_docente():
    operacion = app.openapi()["paths"][
        "/api/v1/gestion/carga-academica/docente/{docente_id}"
    ]["put"]

    schema_ref = operacion["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert schema_ref.endswith("/CargaDocenteUpdate")
    assert operacion["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/CargaDocenteUpdateResponse"
    )
