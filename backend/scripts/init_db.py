# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Inicializa el esquema de la base de datos del backend.

- Primera instalación (sin tabla `alembic_version`): crea el esquema completo
  desde los modelos ORM y marca Alembic en la última revisión.
- Instalación existente (con `alembic_version`): aplica las migraciones
  pendientes con `alembic upgrade head`.

Se ejecuta desde `docker-entrypoint.sh` antes del seed y del servidor. En
desarrollo local el backend también crea tablas con `create_all` en el lifespan.
"""

import asyncio
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402

ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"


def _revision_actual() -> str:
    directorio = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    revision = directorio.get_current_head()
    if revision is None:
        raise RuntimeError("No se encontró ninguna revisión de Alembic.")
    return revision


async def _estado_bd() -> str:
    """Devuelve 'vacia' (sin tablas), 'con_alembic' o 'legacy' (tablas sin versión)."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            tablas = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await engine.dispose()
    if "alembic_version" in tablas:
        return "con_alembic"
    if tablas:
        return "legacy"
    return "vacia"


async def _crear_esquema_y_estampar() -> None:
    import app.adapters.db.models  # noqa: F401 — registra los modelos en Base.metadata
    from app.adapters.db.session import Base

    revision = _revision_actual()
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            ))
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
    finally:
        await engine.dispose()
    print(f"Primera instalación: esquema creado desde los modelos (revisión {revision}).")


def _aplicar_migraciones() -> None:
    from alembic import command

    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    print("Migraciones de Alembic aplicadas.")


def main() -> None:
    estado = asyncio.run(_estado_bd())
    if estado == "con_alembic":
        _aplicar_migraciones()
    elif estado == "vacia":
        asyncio.run(_crear_esquema_y_estampar())
    else:
        raise SystemExit(
            "La base de datos tiene tablas pero no está versionada con Alembic "
            "(no existe alembic_version). Haz un respaldo y marca la revisión que "
            "corresponda antes de continuar:\n"
            "  docker compose exec backend python -m alembic stamp head\n"
            "  docker compose restart backend"
        )


if __name__ == "__main__":
    main()
