# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Entorno de Alembic para migraciones async con SQLAlchemy 2.0 + asyncpg.

Lee la URL de la base de datos desde la configuración de OpenPiar
(variables de entorno / .env) en lugar de hardcodearla en alembic.ini.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importar la configuración de la app para obtener DATABASE_URL
import sys
import os

# Añadir el directorio backend al path para que los imports funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

# Importar todos los modelos ORM para que Alembic los detecte
# IMPORTANTE: estos imports deben estar ANTES de usar Base.metadata
from app.adapters.db.models import (  # noqa: F401 — importar para registrar modelos
    ActaAcuerdoORM,
    AjusteRazonableORM,
    CaracteristicasEstudianteORM,
    CompromisoCasaORM,
    ConfiguracionSistemaORM,
    DerechoDBAORM,
    EntornoHogarORM,
    EntornoSaludORM,
    EstandarEBCORM,
    EstudianteORM,
    MatriculaActualORM,
    PiarORM,
    RecomendacionPMIORM,
    TrayectoriaEducativaORM,
    UsuarioORM,
    SedeORM,
    AsignaturaORM,
    GrupoORM,
    CargaAcademicaORM,
    docente_sedes,
    GradoORM
)
from app.adapters.db.session import Base

# Configuración de logging de Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos ORM — Alembic detecta automáticamente las tablas
target_metadata = Base.metadata

# Sobreescribir URL con la de nuestro .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Modo offline: genera SQL sin conectarse a la BD.
    Útil para revisar qué SQL se ejecutará antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Modo online async: conecta directamente a PostgreSQL y aplica las migraciones.
    Usa create_async_engine para compatibilidad con asyncpg.
    """
    connectable = create_async_engine(settings.DATABASE_URL, echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
