# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Seeder de currículum: carga DBA y EBC desde fixtures JSON a PostgreSQL.

Uso:
    cd backend
    python scripts/seed_curriculum.py

Se ejecuta automáticamente durante el Setup Wizard (Módulo 0).
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.dialects.postgresql import insert

from app.adapters.db.models import DerechoDBAORM, EstandarEBCORM
from app.adapters.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"


async def seed_referentes() -> None:
    """Carga masiva de DBA y EBC en PostgreSQL usando bulk insert."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # --- DBA ---
            dba_path = FIXTURES_DIR / "dba_fixtures.json"
            if dba_path.exists():
                with open(dba_path, "r", encoding="utf-8") as f:
                    dba_data = json.load(f)

                if dba_data:
                    # ON CONFLICT DO NOTHING — idempotente
                    stmt = insert(DerechoDBAORM).values(dba_data)
                    stmt = stmt.on_conflict_do_nothing()
                    await session.execute(stmt)
                    logger.info("✅ DBA cargados: %d registros", len(dba_data))
                else:
                    logger.warning("⚠️  dba_fixtures.json vacío. Ejecuta ingest_curriculum.py primero.")
            else:
                logger.error("❌ No se encontró dba_fixtures.json en %s", FIXTURES_DIR)

            # --- EBC ---
            ebc_path = FIXTURES_DIR / "ebc_fixtures.json"
            if ebc_path.exists():
                with open(ebc_path, "r", encoding="utf-8") as f:
                    ebc_data = json.load(f)

                if ebc_data:
                    stmt = insert(EstandarEBCORM).values(ebc_data)
                    stmt = stmt.on_conflict_do_nothing()
                    await session.execute(stmt)
                    logger.info("✅ EBC cargados: %d registros", len(ebc_data))
                else:
                    logger.warning("⚠️  ebc_fixtures.json vacío.")
            else:
                logger.error("❌ No se encontró ebc_fixtures.json en %s", FIXTURES_DIR)

    logger.info("Sembrado de currículum completado.")


if __name__ == "__main__":
    asyncio.run(seed_referentes())
