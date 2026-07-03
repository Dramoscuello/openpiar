# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Servicio de notificaciones in-app para OpenPiar.

- Genera notificaciones periódicas (cada 6 horas)
- Expone helpers para notificaciones disparadas por eventos del PIAR
"""

import uuid
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    NotificacionORM,
    PiarORM,
    AjusteRazonableORM,
    PeriodoAcademicoORM,
    EstudianteORM,
    UsuarioORM,
    GrupoORM,
    ActaAcuerdoORM,
    ConfiguracionSistemaORM,
)
from app.adapters.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

TIPOS = {
    "inicio_periodo": "inicio_periodo",
    "piar_sin_actualizar": "piar_sin_actualizar",
    "ajuste_sin_puntuacion": "ajuste_sin_puntuacion",
    "piar_estancado": "piar_estancado",
    "firma_pendiente": "firma_pendiente",
    "estudiante_sin_piar": "estudiante_sin_piar",
    "resumen_semanal": "resumen_semanal",
}


async def _crear_notificacion(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    tipo: str,
    titulo: str,
    mensaje: str,
    recurso_url: str | None = None,
) -> None:
    existing = await db.execute(
        select(NotificacionORM).where(
            NotificacionORM.usuario_id == usuario_id,
            NotificacionORM.tipo == tipo,
            NotificacionORM.recurso_url == recurso_url,
            NotificacionORM.leida == False,
        ).limit(1)
    )
    if existing.scalars().first():
        return

    notif = NotificacionORM(
        usuario_id=usuario_id,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        recurso_url=recurso_url,
    )
    db.add(notif)


async def _notificar_piar_sin_actualizar(db: AsyncSession) -> int:
    hoy = date.today()
    limite = hoy - timedelta(days=15)

    periodo_query = select(PeriodoAcademicoORM).where(PeriodoAcademicoORM.activo == True)
    periodo_res = await db.execute(periodo_query)
    periodo = periodo_res.scalars().first()
    if not periodo:
        return 0

    query = (
        select(PiarORM, EstudianteORM)
        .join(EstudianteORM, PiarORM.estudiante_id == EstudianteORM.id)
        .where(
            PiarORM.estado.in_(["en_revision", "firmado"]),
            PiarORM.updated_at < limite,
        )
    )
    result = await db.execute(query)
    rows = result.all()
    count = 0

    ajustes_recientes = await db.execute(
        select(AjusteRazonableORM.piar_id).where(
            AjusteRazonableORM.periodo_id == periodo.id,
        )
    )
    piars_con_ajustes = {r[0] for r in ajustes_recientes.all()}

    for piar, estudiante in rows:
        if piar.id in piars_con_ajustes:
            continue
        if not piar.creado_por:
            continue
        url = f"/estudiantes/{estudiante.id}/piar"
        await _crear_notificacion(
            db, piar.creado_por,
            TIPOS["piar_sin_actualizar"],
            "PIAR sin actualizar",
            f"El PIAR de {estudiante.nombres} {estudiante.apellidos} no tiene ajustes nuevos en los últimos 15 días del periodo activo.",
            url,
        )
        count += 1
    return count


async def _notificar_ajuste_sin_puntuacion(db: AsyncSession) -> int:
    hoy = date.today()

    periodos = await db.execute(
        select(PeriodoAcademicoORM).where(
            PeriodoAcademicoORM.fecha_fin <= hoy + timedelta(days=7),
            PeriodoAcademicoORM.fecha_fin >= hoy,
            PeriodoAcademicoORM.activo == True,
        )
    )
    periodos_cercanos = periodos.scalars().all()
    if not periodos_cercanos:
        return 0

    count = 0
    for periodo in periodos_cercanos:
        ajustes = await db.execute(
            select(AjusteRazonableORM).where(
                AjusteRazonableORM.periodo_id == periodo.id,
                AjusteRazonableORM.puntuacion == None,
            )
        )
        for aj in ajustes.scalars().all():
            if not aj.creado_por:
                continue
            piar = await db.get(PiarORM, aj.piar_id)
            if not piar:
                continue
            url = f"/estudiantes/{piar.estudiante_id}/piar"
            await _crear_notificacion(
                db, aj.creado_por,
                TIPOS["ajuste_sin_puntuacion"],
                "Ajuste sin puntuar",
                f"El periodo {periodo.nombre} finaliza pronto. Puntúa el ajuste de {aj.area} en el PIAR.",
                url,
            )
            count += 1
    return count


async def _notificar_piar_estancado(db: AsyncSession) -> int:
    limite = date.today() - timedelta(days=30)

    query = (
        select(PiarORM, EstudianteORM)
        .join(EstudianteORM, PiarORM.estudiante_id == EstudianteORM.id)
        .where(
            PiarORM.estado == "borrador",
            PiarORM.created_at < limite,
        )
    )
    result = await db.execute(query)
    rows = result.all()
    count = 0

    for piar, estudiante in rows:
        if not piar.creado_por:
            continue
        url = f"/estudiantes/{estudiante.id}/piar"
        await _crear_notificacion(
            db, piar.creado_por,
            TIPOS["piar_estancado"],
            "PIAR estancado en borrador",
            f"El PIAR de {estudiante.nombres} {estudiante.apellidos} lleva más de 30 días en borrador. Revisalo para avanzar.",
            url,
        )
        count += 1
    return count


async def _notificar_firmas_pendientes(db: AsyncSession) -> int:
    query = (
        select(ActaAcuerdoORM, PiarORM, EstudianteORM)
        .join(PiarORM, ActaAcuerdoORM.piar_id == PiarORM.id)
        .join(EstudianteORM, PiarORM.estudiante_id == EstudianteORM.id)
        .where(
            (ActaAcuerdoORM.firmado_estudiante == False)
            | (ActaAcuerdoORM.firmado_acudiente == False)
            | (ActaAcuerdoORM.firmado_docentes_aula == False)
            | (ActaAcuerdoORM.firmado_directivo == False)
        )
    )
    result = await db.execute(query)
    rows = result.all()
    count = 0

    for acta, piar, estudiante in rows:
        directivos = await db.execute(
            select(UsuarioORM).where(UsuarioORM.rol == "directivo")
        )
        url = f"/estudiantes/{estudiante.id}/piar"
        for d in directivos.scalars().all():
            await _crear_notificacion(
                db, d.id,
                TIPOS["firma_pendiente"],
                "Firmas pendientes en PIAR",
                f"El PIAR de {estudiante.nombres} {estudiante.apellidos} tiene firmas pendientes en el acta de acuerdo.",
                url,
            )
            count += 1
    return count


async def _notificar_estudiantes_sin_piar(db: AsyncSession) -> int:
    query = (
        select(EstudianteORM, EntornoSaludORM)
        .join(EntornoSaludORM, EstudianteORM.id == EntornoSaludORM.estudiante_id)
        .where(
            (EntornoSaludORM.tiene_diagnostico_medico == True)
            | (EntornoSaludORM.asiste_terapias == True)
        )
    )
    result = await db.execute(query)
    rows = result.all()
    count = 0

    for estudiante, salud in rows:
        piar_res = await db.execute(
            select(PiarORM).where(PiarORM.estudiante_id == estudiante.id).limit(1)
        )
        if piar_res.scalars().first():
            continue

        if not estudiante.creado_por:
            continue
        url = f"/estudiantes/{estudiante.id}/piar"
        await _crear_notificacion(
            db, estudiante.creado_por,
            TIPOS["estudiante_sin_piar"],
            "Estudiante sin PIAR",
            f"{estudiante.nombres} {estudiante.apellidos} tiene diagnóstico médico pero no se ha creado un PIAR en el periodo activo.",
            url,
        )
        count += 1
    return count


async def _notificar_resumen_semanal(db: AsyncSession) -> int:
    hoy = date.today()
    if hoy.weekday() != 4:
        return 0

    total = await db.execute(select(func.count(PiarORM.id)))
    total_piars = total.scalar() or 0

    activos = await db.execute(
        select(func.count(PiarORM.id)).where(PiarORM.estado.in_(["en_revision", "generando_ia"]))
    )
    piars_activos = activos.scalar() or 0

    firmados = await db.execute(
        select(func.count(PiarORM.id)).where(PiarORM.estado == "firmado")
    )
    piars_firmados = firmados.scalar() or 0

    ajustes_q = await db.execute(select(func.count(AjusteRazonableORM.id)))
    total_ajustes = ajustes_q.scalar() or 0

    directivos = await db.execute(
        select(UsuarioORM).where(UsuarioORM.rol == "directivo")
    )
    for d in directivos.scalars().all():
        await _crear_notificacion(
            db, d.id,
            TIPOS["resumen_semanal"],
            "Resumen semanal de PIARs",
            f"Total PIARs: {total_piars} | Activos: {piars_activos} | Firmados: {piars_firmados} | Ajustes DUA: {total_ajustes}",
            "/dashboard",
        )
    return 1


# ID fijo para el advisory lock de PostgreSQL. Evita que múltiples workers
# de Uvicorn ejecuten el ciclo de notificaciones simultáneamente.
_NOTIF_LOCK_ID = 8294561127


async def ejecutar_notificaciones_periodicas() -> None:
    try:
        async with AsyncSessionLocal() as db:
            lock_result = await db.execute(
                text("SELECT pg_try_advisory_lock(:id)"), {"id": _NOTIF_LOCK_ID}
            )
            if not lock_result.scalar():
                return

            tasks = [
                _notificar_piar_sin_actualizar(db),
                _notificar_ajuste_sin_puntuacion(db),
                _notificar_piar_estancado(db),
                _notificar_firmas_pendientes(db),
                _notificar_estudiantes_sin_piar(db),
                _notificar_resumen_semanal(db),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total = sum(r if isinstance(r, int) else 0 for r in results)
            await db.commit()
            if total > 0:
                logger.info("Notificaciones periódicas: %d generadas", total)
    except Exception as exc:
        logger.error("Error en notificaciones periódicas: %s", exc)


async def inicio_notificaciones_periodicas() -> None:
    await ejecutar_notificaciones_periodicas()


async def notificar_firma_pendiente_evento(
    db: AsyncSession, piar_id: uuid.UUID, estudiante_id: uuid.UUID
) -> None:
    piar = await db.get(PiarORM, piar_id)
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not piar or not estudiante:
        return
    directivos = await db.execute(
        select(UsuarioORM).where(UsuarioORM.rol == "directivo")
    )
    url = f"/estudiantes/{estudiante_id}/piar"
    for d in directivos.scalars().all():
        await _crear_notificacion(
            db, d.id,
            TIPOS["firma_pendiente"],
            "Firmas pendientes en PIAR",
            f"El PIAR de {estudiante.nombres} {estudiante.apellidos} tiene un acta de acuerdo con firmas pendientes.",
            url,
        )


async def notificar_periodo_inicio(db: AsyncSession, periodo_nombre: str) -> None:
    usuarios = await db.execute(select(UsuarioORM))
    url = "/dashboard"
    for u in usuarios.scalars().all():
        await _crear_notificacion(
            db, u.id,
            TIPOS["inicio_periodo"],
            "Periodo académico iniciado",
            f"El periodo {periodo_nombre} ha comenzado. Revisá los PIARs de tus estudiantes para planificar los ajustes DUA.",
            url,
        )
