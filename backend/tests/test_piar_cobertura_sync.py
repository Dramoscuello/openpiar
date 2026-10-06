# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Sincronización de la cobertura PIAR con la carga académica actual."""

from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

from app.entrypoints.api.v1.endpoints.piars import (
    _buscar_cobertura_asignatura,
    _sincronizar_coberturas_periodo,
)

PIAR_ID = uuid4()
GRUPO_ID = uuid4()


class _ScalarsLista:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _ResultadoCargas:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return _ScalarsLista(self._values)


class _DbSync:
    def __init__(self, cargas):
        self._cargas = list(cargas)
        self.agregados = []
        self.flush_llamado = False
        self.execute_llamado = False

    async def execute(self, *args, **kwargs):
        self.execute_llamado = True
        return _ResultadoCargas(self._cargas)

    def add(self, obj):
        self.agregados.append(obj)

    async def flush(self):
        self.flush_llamado = True


def _piar(asignaturas=None, periodos_estado=None):
    periodos = periodos_estado or [(1, "borrador")]
    return NS(
        id=PIAR_ID,
        estado="borrador",
        estudiante=NS(grupo_id=GRUPO_ID),
        asignaturas_estado=list(asignaturas or []),
        periodos=[NS(periodo_id=pid, estado=estado) for pid, estado in periodos],
    )


def _carga(*, asignatura_id=None, nombre="Tecnología", docente_id=None):
    return NS(
        asignatura=NS(
            id=asignatura_id or uuid4(),
            nombre=nombre,
            area=NS(nombre="Tecnología"),
        ),
        docente=NS(id=docente_id or uuid4(), nombre="Deimer", apellido="Ramos"),
    )


@pytest.mark.asyncio
async def test_sincroniza_cobertura_faltante():
    carga = _carga()
    piar = _piar()
    db = _DbSync([carga])

    await _sincronizar_coberturas_periodo(db, piar, NS(id=1))

    assert len(piar.asignaturas_estado) == 1
    cobertura = piar.asignaturas_estado[0]
    assert cobertura.asignatura_id == carga.asignatura.id
    assert cobertura.docente_id == carga.docente.id
    assert cobertura.estado == "pendiente"
    assert cobertura.periodo_id == 1
    assert cobertura.docente_nombre == "Deimer Ramos"
    assert db.flush_llamado


@pytest.mark.asyncio
async def test_no_duplica_cobertura_existente():
    carga = _carga()
    existente = NS(
        asignatura_id=carga.asignatura.id,
        periodo_id=1,
        docente_id=carga.docente.id,
        estado="pendiente",
    )
    piar = _piar(asignaturas=[existente])
    db = _DbSync([carga])

    await _sincronizar_coberturas_periodo(db, piar, NS(id=1))

    assert piar.asignaturas_estado == [existente]
    assert db.agregados == []


@pytest.mark.asyncio
async def test_no_pisa_cobertura_con_ajuste():
    carga = _carga(docente_id=uuid4())
    docente_anterior = uuid4()
    existente = NS(
        asignatura_id=carga.asignatura.id,
        periodo_id=1,
        docente_id=docente_anterior,
        docente_nombre="Docente Anterior",
        estado="con_ajuste",
    )
    piar = _piar(asignaturas=[existente])

    await _sincronizar_coberturas_periodo(_DbSync([carga]), piar, NS(id=1))

    assert existente.docente_id == docente_anterior
    assert existente.docente_nombre == "Docente Anterior"


@pytest.mark.asyncio
async def test_actualiza_docente_sin_ajustes():
    carga = _carga()
    existente = NS(
        asignatura_id=carga.asignatura.id,
        periodo_id=1,
        docente_id=uuid4(),
        docente_nombre="Docente Anterior",
        estado="pendiente",
    )
    piar = _piar(asignaturas=[existente])

    await _sincronizar_coberturas_periodo(_DbSync([carga]), piar, NS(id=1))

    assert existente.docente_id == carga.docente.id
    assert existente.docente_nombre == "Deimer Ramos"
    assert existente.estado == "pendiente"


@pytest.mark.asyncio
async def test_periodo_firmado_no_sincroniza():
    piar = _piar(periodos_estado=[(1, "firmado")])
    db = _DbSync([_carga()])

    await _sincronizar_coberturas_periodo(db, piar, NS(id=1))

    assert db.execute_llamado is False
    assert piar.asignaturas_estado == []


@pytest.mark.asyncio
async def test_tras_sincronizar_el_docente_encuentra_su_cobertura():
    carga = _carga(nombre="Tecnología e Informática")
    piar = _piar()

    await _sincronizar_coberturas_periodo(_DbSync([carga]), piar, NS(id=1))

    cobertura = _buscar_cobertura_asignatura(piar, carga.asignatura.id, "", 1)
    assert cobertura is not None
    assert cobertura.docente_id == carga.docente.id
