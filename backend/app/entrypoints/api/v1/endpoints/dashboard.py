# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoint de Dashboard institucional.
Ruta: /api/v1/dashboard/

Proporciona estadísticas agregadas para la vista de inicio.
Datos institucionales — misma vista para todos los roles.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, union_all, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ActaAcuerdoORM,
    AjusteRazonableORM,
    EstudianteORM,
    GradoORM,
    GrupoORM,
    PeriodoAcademicoORM,
    PiarORM,
)
from app.adapters.db.session import get_db
from app.entrypoints.api.dependencies import CurrentUser
from app.entrypoints.api.schemas import (
    ActividadItem,
    AreaCount,
    DashboardResponse,
    EstadoCount,
    GradoCount,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Estadísticas del dashboard institucional",
)
async def get_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    # ── Conteos básicos ──
    total_estudiantes = await db.scalar(select(func.count(EstudianteORM.id)))
    total_piars = await db.scalar(select(func.count(PiarORM.id)))
    total_ajustes = await db.scalar(select(func.count(AjusteRazonableORM.id)))
    piars_activos = await db.scalar(
        select(func.count(PiarORM.id)).where(
            PiarORM.estado.in_(["borrador", "generando_ia", "en_revision"])
        )
    )
    piars_firmados = await db.scalar(
        select(func.count(PiarORM.id)).where(PiarORM.estado == "firmado")
    )

    # ── Actas con firmas incompletas ──
    actas_firmas_incompletas = await db.scalar(
        select(func.count(ActaAcuerdoORM.id)).where(
            func.not_(
                func.coalesce(ActaAcuerdoORM.firmado_estudiante, False)
                & func.coalesce(ActaAcuerdoORM.firmado_acudiente, False)
                & func.coalesce(ActaAcuerdoORM.firmado_docente_apoyo, False)
                & func.coalesce(ActaAcuerdoORM.firmado_docentes_aula, False)
                & func.coalesce(ActaAcuerdoORM.firmado_directivo, False)
            )
        )
    )

    # ── PIARs por estado ──
    estados_result = await db.execute(
        select(PiarORM.estado, func.count(PiarORM.id)).group_by(PiarORM.estado)
    )
    piars_por_estado = [
        EstadoCount(estado=row[0], total=row[1]) for row in estados_result
    ]

    # ── Ajustes por área ──
    areas_result = await db.execute(
        select(AjusteRazonableORM.area, func.count(AjusteRazonableORM.id)).group_by(
            AjusteRazonableORM.area
        )
    )
    ajustes_por_area = [
        AreaCount(area=row[0], total=row[1]) for row in areas_result
    ]

    # ── Estudiantes por grado ──
    grados_result = await db.execute(
        select(GradoORM.nombre, func.count(EstudianteORM.id))
        .select_from(EstudianteORM)
        .join(EstudianteORM.grupo)
        .join(GrupoORM.grado)
        .group_by(GradoORM.nombre)
        .order_by(GradoORM.nombre)
    )
    estudiantes_por_grado = [
        GradoCount(grado=row[0], total=row[1]) for row in grados_result
    ]

    # ── Periodo activo ──
    periodo_activo = await db.scalar(
        select(PeriodoAcademicoORM).where(PeriodoAcademicoORM.activo == True)  # noqa: E712
    )
    periodo_activo_nombre = periodo_activo.nombre if periodo_activo else None
    ajustes_este_periodo = (
        await db.scalar(
            select(func.count(AjusteRazonableORM.id)).where(
                AjusteRazonableORM.periodo_id == periodo_activo.id
            )
        )
        if periodo_activo
        else 0
    )

    # ── Puntuación promedio ──
    puntuacion_promedio = await db.scalar(
        select(func.avg(AjusteRazonableORM.puntuacion)).where(
            AjusteRazonableORM.puntuacion.isnot(None)
        )
    )

    # ── Actividad reciente: PIARs + Ajustes ──
    ahora = datetime.now().isoformat() + "Z"
    piars_recientes_q = (
        select(
            PiarORM.updated_at,
            literal("piar").label("tipo"),
            func.concat(
                EstudianteORM.nombres, " ", EstudianteORM.apellidos
            ).label("estudiante_nombre"),
            func.concat("PIAR ", PiarORM.estado).label("descripcion"),
        )
        .join(EstudianteORM, PiarORM.estudiante_id == EstudianteORM.id)
        .order_by(PiarORM.updated_at.desc())
        .limit(5)
    )
    ajustes_recientes_q = (
        select(
            AjusteRazonableORM.updated_at,
            literal("ajuste").label("tipo"),
            func.concat(
                EstudianteORM.nombres, " ", EstudianteORM.apellidos
            ).label("estudiante_nombre"),
            func.concat("Ajuste en ", AjusteRazonableORM.area).label("descripcion"),
        )
        .join(PiarORM, AjusteRazonableORM.piar_id == PiarORM.id)
        .join(EstudianteORM, PiarORM.estudiante_id == EstudianteORM.id)
        .order_by(AjusteRazonableORM.updated_at.desc())
        .limit(5)
    )

    union_q = piars_recientes_q.union_all(ajustes_recientes_q)
    actividad_result = await db.execute(
        select(union_q.c.tipo, union_q.c.estudiante_nombre, union_q.c.descripcion, union_q.c.updated_at)
        .order_by(union_q.c.updated_at.desc())
        .limit(10)
    )

    actividad_reciente = [
        ActividadItem(
            tipo=row[0],
            estudiante_nombre=row[1],
            descripcion=row[2],
            fecha=row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3]),
        )
        for row in actividad_result
    ]

    return DashboardResponse(
        total_estudiantes=total_estudiantes or 0,
        total_piars=total_piars or 0,
        total_ajustes=total_ajustes or 0,
        piars_activos=piars_activos or 0,
        piars_firmados=piars_firmados or 0,
        actas_firmas_incompletas=actas_firmas_incompletas or 0,
        piars_por_estado=piars_por_estado,
        ajustes_por_area=ajustes_por_area,
        estudiantes_por_grado=estudiantes_por_grado,
        periodo_activo_nombre=periodo_activo_nombre,
        ajustes_este_periodo=ajustes_este_periodo,
        puntuacion_promedio=round(puntuacion_promedio, 2) if puntuacion_promedio else None,
        actividad_reciente=actividad_reciente,
    )
