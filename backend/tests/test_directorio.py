# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Pruebas del filtrado SQL y agrupación del directorio institucional."""

from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.entrypoints.api.authorization import subquery_grupos_dirigidos
from app.entrypoints.api.v1.endpoints.directorio import (
    _agrupar_contactos,
    listar_directorio,
)

GRUPO_ID = uuid4()
ESTUDIANTE_ID = uuid4()


def _usuario(*, directivo=False, usuario_id=None):
    return NS(id=usuario_id or uuid4(), rol=NS(es_directivo=directivo))


def _fila(
    *,
    key="madre|doc|111",
    nombre="Ana Pérez",
    rol="madre",
    estudiante_id=ESTUDIANTE_ID,
    estudiante_nombres="Lucía",
    estudiante_apellidos="Gómez",
    grado_nombre="Quinto",
    piar_id=None,
    codigo="CODIGO",
    documento="111",
):
    return {
        "contact_key": key,
        "contacto_nombre": nombre,
        "contacto_rol": rol,
        "contacto_telefono": "3001234567",
        "contacto_correo": "ana@example.com",
        "contacto_documento": documento,
        "contacto_principal": True,
        "estudiante_id": estudiante_id,
        "estudiante_nombres": estudiante_nombres,
        "estudiante_apellidos": estudiante_apellidos,
        "grado_nombre": grado_nombre,
        "piar_id": piar_id,
        "codigo_acceso_familia": codigo,
    }


def test_subquery_de_directorio_solo_incluye_grupos_dirigidos():
    usuario = _usuario()
    consulta = subquery_grupos_dirigidos(usuario)

    assert consulta is not None
    texto = str(consulta)
    assert "grupos.director_id" in texto
    assert "carga_academica" not in texto


def test_directivo_no_requiere_subconsulta_de_grupos():
    assert subquery_grupos_dirigidos(_usuario(directivo=True)) is None


def test_agrupar_contactos_no_mezcla_documentos_distintos():
    filas = [
        _fila(estudiante_id=uuid4(), documento="111", key="madre|doc|111"),
        _fila(estudiante_id=uuid4(), documento="222", key="madre|doc|222"),
        _fila(estudiante_id=uuid4(), documento="111", key="madre|doc|111"),
    ]

    contactos = _agrupar_contactos(filas)

    assert len(contactos) == 2
    assert sorted(len(contacto.estudiantes) for contacto in contactos) == [1, 2]


class _Scalars:
    def __init__(self, values):
        self.values = list(values)

    def first(self):
        return self.values[0] if self.values else None

    def all(self):
        return self.values


class _Mappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, *, scalar=None, scalars=None, rows=None):
        self.scalar = scalar
        self._scalars = scalars or []
        self._rows = rows or []

    def scalar_one(self):
        return self.scalar

    def scalars(self):
        return _Scalars(self._scalars)

    def mappings(self):
        return _Mappings(self._rows)


class _DbDirectorio:
    def __init__(self, *, director, rows, total, keys):
        self.director = director
        self.rows = rows
        self.total = total
        self.keys = keys
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        call = len(self.statements)
        if not self.director and call == 1:
            return _Result(scalars=[GRUPO_ID])
        if call == (1 if self.director else 2):
            return _Result(scalar=self.total)
        if call == (2 if self.director else 3):
            return _Result(scalars=self.keys)
        return _Result(rows=self.rows)


@pytest.mark.asyncio
async def test_directorio_filtra_en_sql_y_pagina_contactos():
    usuario = _usuario(directivo=True)
    db = _DbDirectorio(
        director=True,
        rows=[_fila()],
        total=2,
        keys=["madre|doc|111"],
    )

    response = await listar_directorio(
        current_user=usuario,
        db=db,
        skip=1,
        limit=1,
        q="Ana",
    )

    assert response.total == 2
    assert response.skip == 1
    assert response.limit == 1
    assert response.has_next is False
    assert response.contactos[0].estudiantes[0].codigo_acceso_familia == "CODIGO"
    assert "director_id" not in str(db.statements[-1])
    assert "LIKE" in str(db.statements[-1]).upper()


@pytest.mark.asyncio
async def test_director_sin_grupos_recibe_403_sin_consultar_hogares():
    class _Db:
        def __init__(self):
            self.calls = 0

        async def execute(self, _statement):
            self.calls += 1
            return _Result(scalars=[])

    db = _Db()

    with pytest.raises(HTTPException) as error:
        await listar_directorio(current_user=_usuario(), db=db)

    assert error.value.status_code == 403
    assert db.calls == 1


@pytest.mark.asyncio
async def test_directorio_de_director_conserva_filtro_de_grupo_en_sql():
    usuario = _usuario()
    db = _DbDirectorio(
        director=False,
        rows=[_fila()],
        total=1,
        keys=["madre|doc|111"],
    )

    await listar_directorio(
        current_user=usuario, db=db, skip=0, limit=50, q=None
    )

    assert "director_id" in str(db.statements[-1])
    assert "carga_academica" not in str(db.statements[-1])
