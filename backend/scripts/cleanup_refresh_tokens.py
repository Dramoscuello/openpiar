# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Elimina refresh tokens expirados o revocados antiguos.

Uso:
    .venv/bin/python scripts/cleanup_refresh_tokens.py

Puede ejecutarse manualmente o por cron. Conserva los revocados recientes
para permitir la detección de reutilización y la ventana de gracia.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete  # noqa: E402

from app.adapters.db.models import RefreshTokenORM  # noqa: E402
from app.adapters.db.session import AsyncSessionLocal  # noqa: E402

RETENCION_DIAS_REVOCADOS = 7


async def limpiar() -> tuple[int, int]:
    ahora = datetime.now(timezone.utc)
    corte_revocados = ahora - timedelta(days=RETENCION_DIAS_REVOCADOS)

    async with AsyncSessionLocal() as session:
        expirados = await session.execute(
            delete(RefreshTokenORM).where(RefreshTokenORM.expires_at < ahora)
        )
        revocados = await session.execute(
            delete(RefreshTokenORM).where(
                RefreshTokenORM.revoked_at.is_not(None),
                RefreshTokenORM.revoked_at < corte_revocados,
            )
        )
        await session.commit()

    return expirados.rowcount or 0, revocados.rowcount or 0


def main() -> None:
    expirados, revocados = asyncio.run(limpiar())
    print(
        f"Refresh tokens eliminados: {expirados} expirados, "
        f"{revocados} revocados con más de {RETENCION_DIAS_REVOCADOS} días."
    )


if __name__ == "__main__":
    main()
