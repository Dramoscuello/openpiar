# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Vacía las tablas de datos de OpenPiar para pruebas locales (wizard, etc.).

Uso:
    cd backend
    .venv/bin/python scripts/truncate_db.py                    # pide confirmación
    .venv/bin/python scripts/truncate_db.py --yes              # sin confirmación
    .venv/bin/python scripts/truncate_db.py --include-curriculum

Conserva:
- `alembic_version`, para no romper el control de migraciones.
- `derechos_dba` y `estandares_ebc` (currículum), salvo que uses
  `--include-curriculum`.

Con `APP_ENV=production` exige además `--force`.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

TABLAS_PRESERVADAS = {"alembic_version"}
TABLAS_CURRICULUM = {"derechos_dba", "estandares_ebc"}


async def truncar_tablas(*, incluir_curriculum: bool) -> list[str]:
    """Vacía todas las tablas objetivo en una sola sentencia TRUNCATE ... CASCADE."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            tablas = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
            objetivo = [t for t in tablas if t not in TABLAS_PRESERVADAS]
            if not incluir_curriculum:
                objetivo = [t for t in objetivo if t not in TABLAS_CURRICULUM]
            if not objetivo:
                return []

            lista = ", ".join(f'"{t}"' for t in objetivo)
            await conn.execute(text(f"TRUNCATE TABLE {lista} RESTART IDENTITY CASCADE"))
            return sorted(objetivo)
    finally:
        await engine.dispose()


def _confirmar(destino: str) -> bool:
    respuesta = input(f"Se borrarán TODOS los datos de {destino}. ¿Continuar? [y/N]: ")
    return respuesta.strip().lower() in {"y", "yes", "s", "si", "sí"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vacía las tablas de datos de OpenPiar para pruebas locales."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="No pedir confirmación."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Permitir la ejecución aunque APP_ENV=production.",
    )
    parser.add_argument(
        "--include-curriculum",
        action="store_true",
        help="Vaciar también derechos_dba y estandares_ebc.",
    )
    args = parser.parse_args()

    if settings.APP_ENV == "production" and not args.force:
        raise SystemExit(
            "APP_ENV=production: usa --force si de verdad quieres vaciar la base de datos."
        )

    destino = make_url(settings.DATABASE_URL).render_as_string(hide_password=True)
    if not args.yes and not _confirmar(destino):
        raise SystemExit("Cancelado.")

    tablas = asyncio.run(truncar_tablas(incluir_curriculum=args.include_curriculum))
    if not tablas:
        print("No había tablas que vaciar.")
        return

    print(f"Vaciadas {len(tablas)} tablas en {destino}:")
    for tabla in tablas:
        print(f"  - {tabla}")
    if not args.include_curriculum:
        print("(Se conservó el currículum DBA/EBC; usa --include-curriculum para borrarlo.)")


if __name__ == "__main__":
    main()
