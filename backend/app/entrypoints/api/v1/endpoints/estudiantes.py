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

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, UploadFile, File, Form
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import (
    EntornoHogarORM,
    EntornoSaludORM,
    EstudianteORM,
    MatriculaActualORM,
    TrayectoriaEducativaORM,
    GrupoORM,
    GradoORM,
    CargaAcademicaORM,
)
from app.adapters.db.session import get_db
from app.core.exceptions import EstudianteNoEncontradoError, EstudianteYaRegistradoError
from app.domain.entities import Usuario
from app.entrypoints.api.dependencies import CurrentUser, get_estudiante_repo
from app.entrypoints.api.schemas import (
    BaseResponse,
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
from app.core.portable_exporter import (
    serialize_student_data,
    encrypt_data,
    decrypt_data,
    deserialize_and_import_student,
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
    if current_user.rol.es_directivo:
        # Admin: sin filtros
        query = (
            select(EstudianteORM, GrupoORM.director_id, GradoORM.nombre)
            .outerjoin(GrupoORM, GrupoORM.id == EstudianteORM.grupo_id)
            .outerjoin(GradoORM, GradoORM.id == GrupoORM.grado_id)
            .order_by(EstudianteORM.apellidos, EstudianteORM.nombres)
        )
        count_query = select(func.count()).select_from(EstudianteORM)
    else:
        # Docente: filtrar por grupo dirigido o grados donde da clase
        grados_docente_query = select(GrupoORM.grado_id).join(
            CargaAcademicaORM, CargaAcademicaORM.grupo_id == GrupoORM.id
        ).where(CargaAcademicaORM.docente_id == current_user.id)

        grupos_permitidos_query = select(GrupoORM.id).where(
            (GrupoORM.director_id == current_user.id) | 
            (GrupoORM.grado_id.in_(grados_docente_query))
        )

        query = (
            select(EstudianteORM, GrupoORM.director_id, GradoORM.nombre)
            .outerjoin(GrupoORM, GrupoORM.id == EstudianteORM.grupo_id)
            .outerjoin(GradoORM, GradoORM.id == GrupoORM.grado_id)
            .where(EstudianteORM.grupo_id.in_(grupos_permitidos_query))
            .order_by(EstudianteORM.apellidos, EstudianteORM.nombres)
        )

        count_query = select(func.count()).select_from(EstudianteORM).where(
            EstudianteORM.grupo_id.in_(grupos_permitidos_query)
        )

    # Offset y límite
    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    items = []
    for e, director_id, grado_nombre in rows:
        items.append(
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
                grupo_id=e.grupo_id,
                grado=grado_nombre,
                grupo_director_id=director_id,
                created_at=e.created_at,
            )
        )
    return EstudianteListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# Helper: check write permissions on student profiles (Anexo 1)
# ---------------------------------------------------------------------------

async def check_write_permission(current_user: Usuario, db: AsyncSession) -> None:
    """Solo directivos o directores de grupo pueden escribir en Anexo 1."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida."
        )
    if current_user.rol.es_directivo:
        return

    # Verificar si es director de algún grupo
    group_director_result = await db.execute(
        select(GrupoORM).where(GrupoORM.director_id == current_user.id)
    )
    if group_director_result.scalars().first() is not None:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo los directivos o directores de grupo tienen permisos para registrar o editar estudiantes."
    )


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
    await check_write_permission(current_user, repo._session)
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
                grupo_id=body.grupo_id,
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

    grado = None
    if body.grupo_id:
        result = await repo._session.execute(
            select(GrupoORM).options(selectinload(GrupoORM.grado)).where(GrupoORM.id == body.grupo_id)
        )
        grupo_orm = result.scalars().first()
        if grupo_orm and grupo_orm.grado:
            grado = grupo_orm.grado.nombre

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
        grupo_id=estudiante.grupo_id,
        grado=grado,
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

    grado = None
    grupo_director_id = None
    if estudiante.grupo_id:
        result = await repo._session.execute(
            select(GrupoORM).options(selectinload(GrupoORM.grado)).where(GrupoORM.id == estudiante.grupo_id)
        )
        grupo_orm = result.scalars().first()
        if grupo_orm:
            grupo_director_id = grupo_orm.director_id
            if grupo_orm.grado:
                grado = grupo_orm.grado.nombre

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
        grupo_id=estudiante.grupo_id,
        grado=grado,
        grupo_director_id=grupo_director_id,
        created_at=estudiante.created_at,
    )


# ---------------------------------------------------------------------------
# DELETE /estudiantes/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{estudiante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar estudiante",
    description=(
        "Elimina permanentemente el estudiante y todos sus datos relacionados "
        "(salud, hogar, trayectoria, matrícula). Solo directivos o directores de grupo."
    ),
)
async def eliminar_estudiante(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
    repo=Depends(get_estudiante_repo),
) -> None:
    await check_write_permission(current_user, db)
    orm = await db.get(EstudianteORM, estudiante_id)
    if not orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estudiante {estudiante_id} no encontrado.",
        )
    await db.delete(orm)
    await db.commit()


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
    await check_write_permission(current_user, repo._session)
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
    estudiante.grupo_id = body.grupo_id

    # Persistir
    await repo.save(estudiante)

    grado = None
    if body.grupo_id:
        result = await repo._session.execute(
            select(GrupoORM).options(selectinload(GrupoORM.grado)).where(GrupoORM.id == body.grupo_id)
        )
        grupo_orm = result.scalars().first()
        if grupo_orm and grupo_orm.grado:
            grado = grupo_orm.grado.nombre

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
        grupo_id=estudiante.grupo_id,
        grado=grado,
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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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


@router.post(
    "/{estudiante_id}/salud/soporte",
    response_model=BaseResponse,
    summary="Subir soporte médico del diagnóstico en PDF",
)
async def subir_soporte_medico(
    estudiante_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> BaseResponse:
    await check_write_permission(current_user, db)
    
    # Validar formato de archivo
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de soporte debe ser un PDF (.pdf).",
        )
        
    # Validar tamaño máximo (10 MB)
    contenido = await file.read()
    if len(contenido) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El soporte médico no puede superar los 10 MB.",
        )
        
    result = await db.execute(
        select(EntornoSaludORM).where(EntornoSaludORM.estudiante_id == estudiante_id)
    )
    salud = result.scalars().first()
    if not salud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Primero debes crear el entorno de salud del estudiante.",
        )
        
    salud.soporte_medico_nombre = file.filename
    salud.soporte_medico_archivo = contenido
    
    await db.flush()
    return BaseResponse(
        success=True,
        message=f"Soporte médico '{file.filename}' cargado exitosamente."
    )


@router.get(
    "/{estudiante_id}/salud/soporte",
    summary="Descargar soporte médico del diagnóstico",
)
async def descargar_soporte_medico(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EntornoSaludORM).where(EntornoSaludORM.estudiante_id == estudiante_id)
    )
    salud = result.scalars().first()
    if not salud or not salud.soporte_medico_archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soporte médico no encontrado para este estudiante.",
        )
        
    return Response(
        content=salud.soporte_medico_archivo,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{salud.soporte_medico_nombre}"'
        }
    )


@router.delete(
    "/{estudiante_id}/salud/soporte",
    response_model=BaseResponse,
    summary="Eliminar soporte médico del diagnóstico",
)
async def eliminar_soporte_medico(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> BaseResponse:
    await check_write_permission(current_user, db)
    result = await db.execute(
        select(EntornoSaludORM).where(EntornoSaludORM.estudiante_id == estudiante_id)
    )
    salud = result.scalars().first()
    if not salud or not salud.soporte_medico_archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estudiante no tiene soporte médico registrado.",
        )
        
    salud.soporte_medico_nombre = None
    salud.soporte_medico_archivo = None
    
    await db.flush()
    return BaseResponse(
        success=True,
        message="Soporte médico eliminado exitosamente."
    )


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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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
    await check_write_permission(current_user, db)
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


@router.get(
    "/{estudiante_id}/exportar",
    summary="Exportar expediente completo del estudiante en un archivo encriptado .openpiar",
)
async def exportar_estudiante(
    estudiante_id: uuid.UUID,
    password: str = Query(..., min_length=6, description="Contraseña para cifrar el archivo (mínimo 6 caracteres)"),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    # Validar permisos
    if not current_user.rol.es_directivo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol directivo/administrativo pueden exportar expedientes."
        )
        
    estudiante = await db.get(EstudianteORM, estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        
    try:
        data = await serialize_student_data(db, estudiante_id)
        encrypted_bytes = encrypt_data(data, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar: {str(e)}")
        
    filename = f"estudiante_{estudiante.numero_documento}.openpiar"
    return Response(
        content=encrypted_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post(
    "/importar",
    response_model=BaseResponse,
    summary="Importar expediente completo cifrado de un estudiante (.openpiar)",
)
async def importar_estudiante(
    file: UploadFile = File(...),
    password: str = Form(...),
    grupo_id: Optional[uuid.UUID] = Form(None),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> BaseResponse:
    # Validar permisos
    if not current_user.rol.es_directivo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol directivo/administrativo pueden importar expedientes."
        )
        
    # Validar formato
    if not file.filename.endswith(".openpiar"):
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo inválido. Debe ser un archivo con extensión .openpiar"
        )
        
    try:
        encrypted_bytes = await file.read()
        decrypted_data = decrypt_data(encrypted_bytes, password)
        estudiante = await deserialize_and_import_student(
            db, decrypted_data, grupo_id, current_user.id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al importar archivo: {str(e)}")
        
    return BaseResponse(
        success=True,
        message=f"Estudiante {estudiante.nombres} {estudiante.apellidos} importado exitosamente con su historial."
    )
