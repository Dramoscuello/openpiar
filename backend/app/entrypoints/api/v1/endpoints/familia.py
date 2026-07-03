# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.adapters.db.models import (
    EstudianteORM,
    PiarORM,
    AjusteRazonableORM,
    PeriodoAcademicoORM,
    ActaAcuerdoORM,
    GrupoORM,
    GradoORM,
    ConfiguracionSistemaORM,
    EntornoSaludORM,
    EntornoHogarORM,
    TrayectoriaEducativaORM,
    MatriculaActualORM,
    CargaAcademicaORM,
    AsignaturaORM,
    EvidenciaAjusteORM,
    RecomendacionPMIORM,
)
from app.adapters.db.session import get_db
from app.entrypoints.api.schemas import (
    FamiliaPIARResponse,
    FamiliaAjusteResponse,
    FamiliaCompromisoResponse,
    FirmaFamiliaRequest,
)

router = APIRouter(prefix="/familia", tags=["familia"])


def _gen_codigo() -> str:
    import secrets
    return secrets.token_hex(4)[:8]


@router.get("/{codigo}", response_model=FamiliaPIARResponse)
async def get_piar_familia(
    codigo: str,
    db: AsyncSession = Depends(get_db),
):
    estudiante_query = (
        select(EstudianteORM)
        .where(EstudianteORM.codigo_acceso_familia == codigo)
        .options(selectinload(EstudianteORM.grupo).selectinload(GrupoORM.grado))
    )
    result = await db.execute(estudiante_query)
    estudiante = result.scalars().first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Código de acceso no válido.")

    piar_query = (
        select(PiarORM)
        .where(PiarORM.estudiante_id == estudiante.id)
        .options(
            selectinload(PiarORM.ajustes_razonables),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa),
            selectinload(PiarORM.caracteristicas),
        )
        .order_by(PiarORM.created_at.desc())
    )
    piar_result = await db.execute(piar_query)
    piar = piar_result.scalars().first()
    if not piar:
        raise HTTPException(status_code=404, detail="El estudiante no tiene un PIAR activo.")

    periodo_query = select(PeriodoAcademicoORM).where(PeriodoAcademicoORM.activo == True)
    periodo_result = await db.execute(periodo_query)
    periodo_activo = periodo_result.scalars().first()

    grado_nombre = estudiante.grupo.grado.nombre if (
        estudiante.grupo and estudiante.grupo.grado
    ) else None

    ajustes = []
    for a in piar.ajustes_razonables:
        ajustes.append(FamiliaAjusteResponse(
            area=a.area,
            titulo_tema=a.titulo_tema,
            objetivos_propositos=a.objetivos_propositos,
            ajustes_estrategias=a.ajustes_estrategias,
            puntuacion=a.puntuacion,
        ))

    compromisos = []
    if piar.acta_acuerdo:
        for c in piar.acta_acuerdo.compromisos_casa:
            compromisos.append(FamiliaCompromisoResponse(
                nombre_actividad=c.nombre_actividad,
                descripcion_estrategia=c.descripcion_estrategia,
                frecuencia=c.frecuencia,
            ))

    acta = piar.acta_acuerdo

    return FamiliaPIARResponse(
        estudiante_nombre=f"{estudiante.nombres} {estudiante.apellidos}",
        grado=grado_nombre,
        anio_lectivo=piar.anio_lectivo,
        estado=piar.estado,
        periodo_activo=periodo_activo.nombre if periodo_activo else None,
        caracteristicas_descripcion=(
            f"{piar.caracteristicas.descripcion_gustos_intereses}; "
            f"{piar.caracteristicas.descripcion_habilidades}"
            if piar.caracteristicas else None
        ),
        ajustes=ajustes,
        compromisos_casa=compromisos,
        firmado_estudiante=acta.firmado_estudiante if acta else False,
        firmado_acudiente=acta.firmado_acudiente if acta else False,
        firmado_docente_apoyo=acta.firmado_docente_apoyo if acta else False,
        firmado_docentes_aula=acta.firmado_docentes_aula if acta else False,
        firmado_directivo=acta.firmado_directivo if acta else False,
    )


@router.post("/{codigo}/firmar")
async def firmar_acta_familia(
    codigo: str,
    data: FirmaFamiliaRequest,
    db: AsyncSession = Depends(get_db),
):
    estudiante_query = (
        select(EstudianteORM)
        .where(EstudianteORM.codigo_acceso_familia == codigo)
    )
    result = await db.execute(estudiante_query)
    estudiante = result.scalars().first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Código de acceso no válido.")

    piar_query = (
        select(PiarORM)
        .where(PiarORM.estudiante_id == estudiante.id)
        .options(selectinload(PiarORM.acta_acuerdo))
        .order_by(PiarORM.created_at.desc())
    )
    piar_result = await db.execute(piar_query)
    piar = piar_result.scalars().first()
    if not piar or not piar.acta_acuerdo:
        raise HTTPException(status_code=404, detail="No hay acta de acuerdo para firmar.")

    if data.rol == "estudiante":
        piar.acta_acuerdo.firmado_estudiante = True
    elif data.rol == "acudiente":
        piar.acta_acuerdo.firmado_acudiente = True

    await db.commit()
    return {"success": True, "message": f"Firma como {data.rol} registrada correctamente."}


@router.get("/{codigo}/acta/pdf")
async def get_acta_pdf_familia(
    codigo: str,
    db: AsyncSession = Depends(get_db),
):
    estudiante_query = (
        select(EstudianteORM)
        .where(EstudianteORM.codigo_acceso_familia == codigo)
    )
    result = await db.execute(estudiante_query)
    estudiante_orm = result.scalars().first()
    if not estudiante_orm:
        raise HTTPException(status_code=404, detail="Código de acceso no válido.")

    piar_query = (
        select(PiarORM)
        .where(PiarORM.estudiante_id == estudiante_orm.id)
        .options(
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.grado),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.sede),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.asignatura),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_salud),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_hogar),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.trayectoria_educativa),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.matricula_actual),
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.periodo),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias).selectinload(EvidenciaAjusteORM.creador),
            selectinload(PiarORM.recomendaciones_pmi),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa),
        )
        .order_by(PiarORM.created_at.desc())
    )
    piar_result = await db.execute(piar_query)
    piar = piar_result.scalars().first()
    if not piar or not piar.acta_acuerdo:
        raise HTTPException(status_code=404, detail="El estudiante no tiene un PIAR con acta firmada.")

    from datetime import date
    periodos_result = await db.execute(
        select(PeriodoAcademicoORM).order_by(PeriodoAcademicoORM.fecha_inicio)
    )
    all_periodos = periodos_result.scalars().all()
    periods_with_adjustments = {aj.periodo_id for aj in piar.ajustes_razonables if aj.periodo_id}

    selected_periods = []
    today = date.today()
    for p in all_periodos:
        if p.activo or p.fecha_inicio <= today or p.id in periods_with_adjustments:
            selected_periods.append(p)

    config_result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = config_result.scalars().first()

    from app.core.pdf_generator import generate_acta_pdf
    pdf_bytes = generate_acta_pdf(piar, config, selected_periods)

    filename = f"PIAR_{estudiante_orm.numero_documento}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
