#!/bin/bash
set -e

echo "==> OpenPiar backend: esperando a que PostgreSQL este listo..."

until python -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

async def check():
    s = get_settings()
    engine = create_async_engine(s.DATABASE_URL.split('?')[0] if '?' in s.DATABASE_URL else s.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
    await engine.dispose()

asyncio.run(check())
"; do
    echo "   PostgreSQL no responde todavia. Reintentando en 2s..."
    sleep 2
done

echo "==> PostgreSQL listo."

echo "==> Sembrando curriculo nacional (DBA y EBC)..."
python scripts/seed_curriculum.py || echo "   (el seed ya estaba aplicado o no era necesario)"

echo "==> Iniciando Uvicorn en puerto 8000..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
