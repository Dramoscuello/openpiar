# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de Estudiantes — Anexo 1 completo.
Ruta: /api/v1/estudiantes/

Cubre:
- CRUD del estudiante (info general)
- Entorno de salud (sección 2 del Anexo 1)
- Entorno de hogar (sección 3 del Anexo 1)
- Trayectoria educativa (sección 4 del Anexo 1)
- Matrícula actual (sección 4 del Anexo 1)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    EntornoHogarORM,
    EntornoSaludORM,
    EstudianteORM,
    MatriculaActualORM,
    TrayectoriaEducativaORM,
)
from app.adapters.db.session import get_db
from app.core.exceptions import EstudianteNoEncontradoError, EstudianteYaRegistradoError
from app.entrypoints.api.dependencies import CurrentUser, get_estudiante_repo
from app.entrypoints.api.schemas import (
    CrearEstudianteRequest,
    EntornoHogarRequest,
    EntornoHogarResponse,
    EntornoSaludRequest,
    EntornoSaludResponse,
    EstudianteListResponse,
    EstudianteResponse,
    TrayectoriaEducativaRequest,
    TrayectoriaEducativaResponse,
    MatriculaActualRequest,
    MatriculaActualResponse,
)
from app.use_cases.estudiantes.crear_estudiante import (
    CrearEstudianteInput,
    CrearEstudianteUseCase,
)

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes — Anexo 1"])


# ---------------------------------------------------------------------------
# GET /estudiantes — Listar
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=EstudianteListResponse,
    summary="Listar estudiantes",
)
async def listar_estudiantes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = None,
    repo=Depends(get_estudiante_repo),
    db: AsyncSession = Depends(get_db),
) -> EstudianteListResponse:
    estudiantes = await repo.list_all(skip=skip, limit=limit)
    total = await repo.count()
    items = [
        EstudianteResponse(
            id=e.id,
            nombres=e.nombres,
            apellidos=e.apellidos,
            tipo_documento=e.tipo_documento,
            numero_documento=e.numero_documento,
            fecha_nacimiento=e.fecha_nacimiento,
            edad=e.edad,
            departamento_residencia=e.departamento_residencia,
            municipio_residencia=e.municipio_residencia,
            direccion=e.direccion,
            barrio_vereda=e.barrio_vereda,
            lugar_nacimiento=e.lugar_nacimiento,
            telefono=e.telefono,
            correo=e.correo,
            en_centro_proteccion=e.en_centro_proteccion,
            centro_proteccion_donde=e.centro_proteccion_donde,
            grupo_etnico=e.grupo_etnico,
            victima_conflicto=e.victima_conflicto,
            registro_victima=e.registro_victima,
            created_at=e.created_at,
        )
        for e in estudiantes
    ]
    return EstudianteListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# POST /estudiantes — Crear
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=EstudianteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo estudiante",
    description=(
        "Registra un estudiante beneficiario del PIAR. "
        "Corresponde al inicio del diligenciamiento del Anexo 1 "
        "(Decreto 1421 de 2017)."
    ),
)
async def crear_estudiante(
    body: CrearEstudianteRequest,
    current_user: CurrentUser = None,
    repo=Depends(get_estudiante_repo),
) -> EstudianteResponse:
    use_case = CrearEstudianteUseCase(repo)
    try:
        estudiante = await use_case.execute(
            CrearEstudianteInput(
                nombres=body.nombres,
                apellidos=body.apellidos,
                tipo_documento=body.tipo_documento,
                numero_documento=body.numero_documento,
                fecha_nacimiento=body.fecha_nacimiento,
                edad=body.edad,
                departamento_residencia=body.departamento_residencia,
                municipio_residencia=body.municipio_residencia,
                direccion=body.direccion,
                barrio_vereda=body.barrio_vereda,
                creado_por=current_user.id if current_user else None,
                lugar_nacimiento=body.lugar_nacimiento,
                telefono=body.telefono,
                correo=str(body.correo) if body.correo else None,
                en_centro_proteccion=body.en_centro_proteccion,
                centro_proteccion_donde=body.centro_proteccion_donde,
                grupo_etnico=body.grupo_etnico,
                victima_conflicto=body.victima_conflicto,
                registro_victima=body.registro_victima,
            )
        )
    except EstudianteYaRegistradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return EstudianteResponse(
        id=estudiante.id,
        nombres=estudiante.nombres,
        apellidos=estudiante.apellidos,
        tipo_documento=estudiante.tipo_documento,
        numero_documento=estudiante.numero_documento,
        fecha_nacimiento=estudiante.fecha_nacimiento,
        edad=estudiante.edad,
        departamento_residencia=estudiante.departamento_residencia,
        municipio_residencia=estudiante.municipio_residencia,
        direccion=estudiante.direccion,
        barrio_vereda=estudiante.barrio_vereda,
        lugar_nacimiento=estudiante.lugar_nacimiento,
        telefono=estudiante.telefono,
        correo=estudiante.correo,
        en_centro_proteccion=estudiante.en_centro_proteccion,
        centro_proteccion_donde=estudiante.centro_proteccion_donde,
        grupo_etnico=estudiante.grupo_etnico,
        victima_conflicto=estudiante.victima_conflicto,
        registro_victima=estudiante.registro_victima,
        created_at=estudiante.created_at,
    )


# ---------------------------------------------------------------------------
# GET /estudiantes/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{estudiante_id}",
    response_model=EstudianteResponse,
    summary="Obtener estudiante por ID",
)
async def obtener_estudiante(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    repo=Depends(get_estudiante_repo),
) -> EstudianteResponse:
    estudiante = await repo.find_by_id(estudiante_id)
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estudiante {estudiante_id} no encontrado.",
        )
    return EstudianteResponse(
        id=estudiante.id,
        nombres=estudiante.nombres,
        apellidos=estudiante.apellidos,
        tipo_documento=estudiante.tipo_documento,
        numero_documento=estudiante.numero_documento,
        fecha_nacimiento=estudiante.fecha_nacimiento,
        edad=estudiante.edad,
        departamento_residencia=estudiante.departamento_residencia,
        municipio_residencia=estudiante.municipio_residencia,
        direccion=estudiante.direccion,
        barrio_vereda=estudiante.barrio_vereda,
        lugar_nacimiento=estudiante.lugar_nacimiento,
        telefono=estudiante.telefono,
        correo=estudiante.correo,
        en_centro_proteccion=estudiante.en_centro_proteccion,
        centro_proteccion_donde=estudiante.centro_proteccion_donde,
        grupo_etnico=estudiante.grupo_etnico,
        victima_conflicto=estudiante.victima_conflicto,
        registro_victima=estudiante.registro_victima,
        created_at=estudiante.created_at,
    )


# ---------------------------------------------------------------------------
# PATCH /estudiantes/{id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{estudiante_id}",
    response_model=EstudianteResponse,
    summary="Actualizar datos generales del estudiante",
)
async def actualizar_estudiante(
    estudiante_id: uuid.UUID,
    body: CrearEstudianteRequest,
    current_user: CurrentUser = None,
    repo=Depends(get_estudiante_repo),
) -> EstudianteResponse:
    estudiante = await repo.find_by_id(estudiante_id)
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estudiante {estudiante_id} no encontrado.",
        )

    # Actualizar campos
    estudiante.nombres = body.nombres.strip()
    estudiante.apellidos = body.apellidos.strip()
    estudiante.tipo_documento = body.tipo_documento
    estudiante.numero_documento = body.numero_documento.strip()
    estudiante.fecha_nacimiento = body.fecha_nacimiento
    estudiante.edad = body.edad
    estudiante.departamento_residencia = body.departamento_residencia
    estudiante.municipio_residencia = body.municipio_residencia
    estudiante.direccion = body.direccion
    estudiante.barrio_vereda = body.barrio_vereda
    estudiante.lugar_nacimiento = body.lugar_nacimiento
    estudiante.telefono = body.telefono
    estudiante.correo = str(body.correo) if body.correo else None
    estudiante.en_centro_proteccion = body.en_centro_proteccion
    estudiante.centro_proteccion_donde = body.centro_proteccion_donde
    estudiante.grupo_etnico = body.grupo_etnico
    estudiante.victima_conflicto = body.victima_conflicto
    estudiante.registro_victima = body.registro_victima

    # Persistir
    await repo.save(estudiante)

    return EstudianteResponse(
        id=estudiante.id,
        nombres=estudiante.nombres,
        apellidos=estudiante.apellidos,
        tipo_documento=estudiante.tipo_documento,
        numero_documento=estudiante.numero_documento,
        fecha_nacimiento=estudiante.fecha_nacimiento,
        edad=estudiante.edad,
        departamento_residencia=estudiante.departamento_residencia,
        municipio_residencia=estudiante.municipio_residencia,
        direccion=estudiante.direccion,
        barrio_vereda=estudiante.barrio_vereda,
        lugar_nacimiento=estudiante.lugar_nacimiento,
        telefono=estudiante.telefono,
        correo=estudiante.correo,
        en_centro_proteccion=estudiante.en_centro_proteccion,
        centro_proteccion_donde=estudiante.centro_proteccion_donde,
        grupo_etnico=estudiante.grupo_etnico,
        victima_conflicto=estudiante.victima_conflicto,
        registro_victima=estudiante.registro_victima,
        created_at=estudiante.created_at,
    )


# ---------------------------------------------------------------------------
# Entorno Salud — GET / POST / PATCH
# ---------------------------------------------------------------------------

@router.get(
    "/{estudiante_id}/salud",
    response_model=EntornoSaludResponse,
    summary="Obtener entorno de salud",
)
async def get_entorno_salud(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoSaludResponse:
    result = await db.execute(
        select(EntornoSaludORM).where(EntornoSaludORM.estudiante_id == estudiante_id)
    )
    salud = result.scalars().first()
    if not salud:
        raise HTTPException(status_code=404, detail="Entorno de salud no encontrado.")
    return EntornoSaludResponse.model_validate(salud)


@router.post(
    "/{estudiante_id}/salud",
    response_model=EntornoSaludResponse,
    status_code=201,
    summary="Crear entorno de salud",
)
async def crear_entorno_salud(
    estudiante_id: uuid.UUID,
    body: EntornoSaludRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoSaludResponse:
    # Verificar que el estudiante existe
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    orm = EntornoSaludORM(
        estudiante_id=estudiante_id,
        **body.model_dump(),
    )
    db.add(orm)
    await db.flush()
    await db.refresh(orm)
    return EntornoSaludResponse.model_validate(orm)


@router.patch(
    "/{estudiante_id}/salud",
    response_model=EntornoSaludResponse,
    summary="Actualizar entorno de salud",
)
async def actualizar_entorno_salud(
    estudiante_id: uuid.UUID,
    body: EntornoSaludRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoSaludResponse:
    result = await db.execute(
        select(EntornoSaludORM).where(EntornoSaludORM.estudiante_id == estudiante_id)
    )
    salud = result.scalars().first()
    if not salud:
        raise HTTPException(status_code=404, detail="Entorno de salud no encontrado.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(salud, field, value)

    await db.flush()
    await db.refresh(salud)
    return EntornoSaludResponse.model_validate(salud)


# ---------------------------------------------------------------------------
# Entorno Hogar — GET / POST / PATCH
# ---------------------------------------------------------------------------

@router.get(
    "/{estudiante_id}/hogar",
    response_model=EntornoHogarResponse,
    summary="Obtener entorno de hogar",
)
async def get_entorno_hogar(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoHogarResponse:
    result = await db.execute(
        select(EntornoHogarORM).where(EntornoHogarORM.estudiante_id == estudiante_id)
    )
    hogar = result.scalars().first()
    if not hogar:
        raise HTTPException(status_code=404, detail="Entorno de hogar no encontrado.")
    return EntornoHogarResponse.model_validate(hogar)


@router.post(
    "/{estudiante_id}/hogar",
    response_model=EntornoHogarResponse,
    status_code=201,
    summary="Crear entorno de hogar",
)
async def crear_entorno_hogar(
    estudiante_id: uuid.UUID,
    body: EntornoHogarRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoHogarResponse:
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    orm = EntornoHogarORM(estudiante_id=estudiante_id, **body.model_dump())
    db.add(orm)
    await db.flush()
    await db.refresh(orm)
    return EntornoHogarResponse.model_validate(orm)


@router.patch(
    "/{estudiante_id}/hogar",
    response_model=EntornoHogarResponse,
    summary="Actualizar entorno de hogar",
)
async def actualizar_entorno_hogar(
    estudiante_id: uuid.UUID,
    body: EntornoHogarRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EntornoHogarResponse:
    result = await db.execute(
        select(EntornoHogarORM).where(EntornoHogarORM.estudiante_id == estudiante_id)
    )
    hogar = result.scalars().first()
    if not hogar:
        raise HTTPException(status_code=404, detail="Entorno de hogar no encontrado.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(hogar, field, value)

    await db.flush()
    await db.refresh(hogar)
    return EntornoHogarResponse.model_validate(hogar)


# ---------------------------------------------------------------------------
# Trayectoria Educativa — GET / POST / PATCH
# ---------------------------------------------------------------------------

@router.get(
    "/{estudiante_id}/trayectoria",
    response_model=TrayectoriaEducativaResponse,
    summary="Obtener trayectoria educativa",
)
async def get_trayectoria_educativa(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> TrayectoriaEducativaResponse:
    result = await db.execute(
        select(TrayectoriaEducativaORM).where(TrayectoriaEducativaORM.estudiante_id == estudiante_id)
    )
    trayectoria = result.scalars().first()
    if not trayectoria:
        raise HTTPException(status_code=404, detail="Trayectoria educativa no encontrada.")
    return TrayectoriaEducativaResponse.model_validate(trayectoria)


@router.post(
    "/{estudiante_id}/trayectoria",
    response_model=TrayectoriaEducativaResponse,
    status_code=201,
    summary="Crear trayectoria educativa",
)
async def crear_trayectoria_educativa(
    estudiante_id: uuid.UUID,
    body: TrayectoriaEducativaRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> TrayectoriaEducativaResponse:
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    orm = TrayectoriaEducativaORM(
        estudiante_id=estudiante_id,
        **body.model_dump(),
    )
    db.add(orm)
    await db.flush()
    await db.refresh(orm)
    return TrayectoriaEducativaResponse.model_validate(orm)


@router.patch(
    "/{estudiante_id}/trayectoria",
    response_model=TrayectoriaEducativaResponse,
    summary="Actualizar trayectoria educativa",
)
async def actualizar_trayectoria_educativa(
    estudiante_id: uuid.UUID,
    body: TrayectoriaEducativaRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> TrayectoriaEducativaResponse:
    result = await db.execute(
        select(TrayectoriaEducativaORM).where(TrayectoriaEducativaORM.estudiante_id == estudiante_id)
    )
    trayectoria = result.scalars().first()
    if not trayectoria:
        raise HTTPException(status_code=404, detail="Trayectoria educativa no encontrada.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(trayectoria, field, value)

    await db.flush()
    await db.refresh(trayectoria)
    return TrayectoriaEducativaResponse.model_validate(trayectoria)


# ---------------------------------------------------------------------------
# Matrícula Actual — GET / POST / PATCH
# ---------------------------------------------------------------------------

@router.get(
    "/{estudiante_id}/matricula",
    response_model=MatriculaActualResponse,
    summary="Obtener matrícula actual",
)
async def get_matricula_actual(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> MatriculaActualResponse:
    result = await db.execute(
        select(MatriculaActualORM).where(MatriculaActualORM.estudiante_id == estudiante_id)
    )
    matricula = result.scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula actual no encontrada.")
    return MatriculaActualResponse.model_validate(matricula)


@router.post(
    "/{estudiante_id}/matricula",
    response_model=MatriculaActualResponse,
    status_code=201,
    summary="Crear matrícula actual",
)
async def crear_matricula_actual(
    estudiante_id: uuid.UUID,
    body: MatriculaActualRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> MatriculaActualResponse:
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    orm = MatriculaActualORM(
        estudiante_id=estudiante_id,
        **body.model_dump(),
    )
    db.add(orm)
    await db.flush()
    await db.refresh(orm)
    return MatriculaActualResponse.model_validate(orm)


@router.patch(
    "/{estudiante_id}/matricula",
    response_model=MatriculaActualResponse,
    summary="Actualizar matrícula actual",
)
async def actualizar_matricula_actual(
    estudiante_id: uuid.UUID,
    body: MatriculaActualRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> MatriculaActualResponse:
    result = await db.execute(
        select(MatriculaActualORM).where(MatriculaActualORM.estudiante_id == estudiante_id)
    )
    matricula = result.scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula actual no encontrada.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(matricula, field, value)

    await db.flush()
    await db.refresh(matricula)
    return MatriculaActualResponse.model_validate(matricula)
