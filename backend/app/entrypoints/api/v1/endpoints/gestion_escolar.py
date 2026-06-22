# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de Gestión Escolar — Sedes, Docentes, Asignaturas, Grupos y Carga Académica.
Ruta: /api/v1/gestion/
"""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.session import get_db
from app.adapters.db.models import (
    UsuarioORM,
    SedeORM,
    AsignaturaORM,
    GrupoORM,
    CargaAcademicaORM
)
from app.entrypoints.api.dependencies import CurrentUser, DirectivoUser
from app.core.security import get_password_hash

router = APIRouter(prefix="/gestion", tags=["Gestión Escolar"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class SedeCreate(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None

class SedeResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    direccion: Optional[str]
    telefono: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DocenteCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    apellido: str
    rol: str # docente_aula, docente_apoyo, orientador
    cargo: Optional[str] = "Docente"
    sede_ids: List[uuid.UUID]

class DocenteResponse(BaseModel):
    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    rol: str
    cargo: Optional[str]
    sedes: List[SedeResponse]

    class Config:
        from_attributes = True

class AsignaturaCreate(BaseModel):
    nombre: str

class AsignaturaResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    created_at: datetime

    class Config:
        from_attributes = True

class GrupoCreate(BaseModel):
    nombre: str
    grado: str
    sede_id: uuid.UUID
    director_id: Optional[uuid.UUID] = None

class GrupoResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    grado: str
    sede: SedeResponse
    director: Optional[dict] = None # Simple representation of director

    class Config:
        from_attributes = True

class CargaAcademicaCreate(BaseModel):
    docente_id: uuid.UUID
    asignatura_id: uuid.UUID
    grupo_id: uuid.UUID

class CargaAcademicaResponse(BaseModel):
    id: uuid.UUID
    docente_id: uuid.UUID
    docente_nombre: str
    asignatura: AsignaturaResponse
    grupo: GrupoResponse

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Sedes Endpoints
# ---------------------------------------------------------------------------

@router.get("/sedes", response_model=List[SedeResponse])
async def list_sedes(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SedeORM).order_by(SedeORM.nombre))
    return result.scalars().all()

@router.post("/sedes", response_model=SedeResponse, status_code=status.HTTP_201_CREATED)
async def create_sede(
    body: SedeCreate,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    sede = SedeORM(
        nombre=body.nombre,
        direccion=body.direccion,
        telefono=body.telefono
    )
    db.add(sede)
    await db.commit()
    await db.refresh(sede)
    return sede


# ---------------------------------------------------------------------------
# Docentes Endpoints
# ---------------------------------------------------------------------------

@router.get("/docentes", response_model=List[DocenteResponse])
async def list_docentes(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    # Select all users that have teacher roles
    result = await db.execute(
        select(UsuarioORM)
        .where(UsuarioORM.rol.in_(["docente_aula", "docente_apoyo", "orientador"]))
        .options(selectinload(UsuarioORM.sedes))
        .order_by(UsuarioORM.apellido, UsuarioORM.nombre)
    )
    return result.scalars().all()

@router.post("/docentes", response_model=DocenteResponse, status_code=status.HTTP_201_CREATED)
async def create_docente(
    body: DocenteCreate,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    # Check if user already exists
    exists_result = await db.execute(select(UsuarioORM).where(UsuarioORM.email == body.email))
    if exists_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con este correo electrónico."
        )

    if body.rol not in ["docente_aula", "docente_apoyo", "orientador"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol debe ser docente_aula, docente_apoyo u orientador."
        )

    # Fetch sedes to link
    sedes_result = await db.execute(select(SedeORM).where(SedeORM.id.in_(body.sede_ids)))
    sedes = sedes_result.scalars().all()
    if len(sedes) != len(body.sede_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Una o más sedes especificadas no existen."
        )

    docente = UsuarioORM(
        email=body.email,
        password_hash=get_password_hash(body.password),
        nombre=body.nombre,
        apellido=body.apellido,
        rol=body.rol,
        cargo=body.cargo,
        sedes=sedes
    )

    db.add(docente)
    await db.commit()
    
    # Reload with relations eagerly loaded to prevent lazy-load issues during serialization
    result = await db.execute(
        select(UsuarioORM)
        .where(UsuarioORM.id == docente.id)
        .options(selectinload(UsuarioORM.sedes))
    )
    docente_completo = result.scalars().one()
    return docente_completo


# ---------------------------------------------------------------------------
# Asignaturas Endpoints
# ---------------------------------------------------------------------------

@router.get("/asignaturas", response_model=List[AsignaturaResponse])
async def list_asignaturas(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AsignaturaORM).order_by(AsignaturaORM.nombre))
    return result.scalars().all()

@router.post("/asignaturas", response_model=AsignaturaResponse, status_code=status.HTTP_201_CREATED)
async def create_asignatura(
    body: AsignaturaCreate,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    # Check uniqueness
    exists_result = await db.execute(select(AsignaturaORM).where(AsignaturaORM.nombre == body.nombre))
    if exists_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta asignatura ya está registrada."
        )

    asignatura = AsignaturaORM(nombre=body.nombre)
    db.add(asignatura)
    await db.commit()
    await db.refresh(asignatura)
    return asignatura


# ---------------------------------------------------------------------------
# Grupos Endpoints
# ---------------------------------------------------------------------------

@router.get("/grupos", response_model=List[GrupoResponse])
async def list_grupos(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GrupoORM)
        .options(selectinload(GrupoORM.sede), selectinload(GrupoORM.director))
        .order_by(GrupoORM.grado, GrupoORM.nombre)
    )
    grupos = result.scalars().all()
    
    response = []
    for g in grupos:
        director_dict = None
        if g.director:
            director_dict = {
                "id": str(g.director.id),
                "nombre": g.director.nombre,
                "apellido": g.director.apellido,
                "email": g.director.email
            }
        response.append(GrupoResponse(
            id=g.id,
            nombre=g.nombre,
            grado=g.grado,
            sede=SedeResponse.from_orm(g.sede),
            director=director_dict
        ))
    return response

@router.post("/grupos", response_model=GrupoResponse, status_code=status.HTTP_201_CREATED)
async def create_grupo(
    body: GrupoCreate,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    # Verify Sede exists
    sede_result = await db.execute(select(SedeORM).where(SedeORM.id == body.sede_id))
    sede = sede_result.scalars().first()
    if not sede:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sede especificada no existe."
        )

    # Verify director (if provided) exists
    director = None
    if body.director_id:
        dir_result = await db.execute(select(UsuarioORM).where(UsuarioORM.id == body.director_id))
        director = dir_result.scalars().first()
        if not director:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El director de grupo especificado no existe."
            )

    # Check unique constraint (nombre, grado, sede_id)
    exists = await db.execute(
        select(GrupoORM).where(
            GrupoORM.nombre == body.nombre,
            GrupoORM.grado == body.grado,
            GrupoORM.sede_id == body.sede_id
        )
    )
    if exists.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un grupo con ese nombre y grado en esta sede."
        )

    grupo = GrupoORM(
        nombre=body.nombre,
        grado=body.grado,
        sede_id=body.sede_id,
        director_id=body.director_id
    )
    db.add(grupo)
    await db.commit()
    await db.refresh(grupo)
    
    # Reload with relations
    result = await db.execute(
        select(GrupoORM)
        .where(GrupoORM.id == grupo.id)
        .options(selectinload(GrupoORM.sede), selectinload(GrupoORM.director))
    )
    g = result.scalars().one()
    
    director_dict = None
    if g.director:
        director_dict = {
            "id": str(g.director.id),
            "nombre": g.director.nombre,
            "apellido": g.director.apellido,
            "email": g.director.email
        }
        
    return GrupoResponse(
        id=g.id,
        nombre=g.nombre,
        grado=g.grado,
        sede=SedeResponse.from_orm(g.sede),
        director=director_dict
    )


# ---------------------------------------------------------------------------
# Carga Académica Endpoints
# ---------------------------------------------------------------------------

@router.get("/carga-academica", response_model=List[CargaAcademicaResponse])
async def list_carga_academica(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CargaAcademicaORM)
        .options(
            selectinload(CargaAcademicaORM.docente),
            selectinload(CargaAcademicaORM.asignatura),
            selectinload(CargaAcademicaORM.grupo).selectinload(GrupoORM.sede),
            selectinload(CargaAcademicaORM.grupo).selectinload(GrupoORM.director)
        )
    )
    cargas = result.scalars().all()
    
    response = []
    for c in cargas:
        director_dict = None
        if c.grupo.director:
            director_dict = {
                "id": str(c.grupo.director.id),
                "nombre": c.grupo.director.nombre,
                "apellido": c.grupo.director.apellido,
                "email": c.grupo.director.email
            }
        
        response.append(CargaAcademicaResponse(
            id=c.id,
            docente_id=c.docente_id,
            docente_nombre=f"{c.docente.nombre} {c.docente.apellido}",
            asignatura=AsignaturaResponse.from_orm(c.asignatura),
            grupo=GrupoResponse(
                id=c.grupo.id,
                nombre=c.grupo.nombre,
                grado=c.grupo.grado,
                sede=SedeResponse.from_orm(c.grupo.sede),
                director=director_dict
            )
        ))
    return response

@router.post("/carga-academica", response_model=CargaAcademicaResponse, status_code=status.HTTP_201_CREATED)
async def create_carga_academica(
    body: CargaAcademicaCreate,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    # Verify Docente exists
    doc_result = await db.execute(select(UsuarioORM).where(UsuarioORM.id == body.docente_id))
    docente = doc_result.scalars().first()
    if not docente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El docente no existe.")

    # Verify Asignatura exists
    asig_result = await db.execute(select(AsignaturaORM).where(AsignaturaORM.id == body.asignatura_id))
    asignatura = asig_result.scalars().first()
    if not asignatura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La asignatura no existe.")

    # Verify Grupo exists
    grupo_result = await db.execute(select(GrupoORM).where(GrupoORM.id == body.grupo_id))
    grupo = grupo_result.scalars().first()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El grupo no existe.")

    # Check unique constraint
    exists = await db.execute(
        select(CargaAcademicaORM).where(
            CargaAcademicaORM.docente_id == body.docente_id,
            CargaAcademicaORM.asignatura_id == body.asignatura_id,
            CargaAcademicaORM.grupo_id == body.grupo_id
        )
    )
    if exists.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta asignación de carga académica ya existe."
        )

    carga = CargaAcademicaORM(
        docente_id=body.docente_id,
        asignatura_id=body.asignatura_id,
        grupo_id=body.grupo_id
    )
    db.add(carga)
    await db.commit()
    await db.refresh(carga)
    
    # Reload with relations
    result = await db.execute(
        select(CargaAcademicaORM)
        .where(CargaAcademicaORM.id == carga.id)
        .options(
            selectinload(CargaAcademicaORM.docente),
            selectinload(CargaAcademicaORM.asignatura),
            selectinload(CargaAcademicaORM.grupo).selectinload(GrupoORM.sede),
            selectinload(CargaAcademicaORM.grupo).selectinload(GrupoORM.director)
        )
    )
    c = result.scalars().one()
    
    director_dict = None
    if c.grupo.director:
        director_dict = {
            "id": str(c.grupo.director.id),
            "nombre": c.grupo.director.nombre,
            "apellido": c.grupo.director.apellido,
            "email": c.grupo.director.email
        }
        
    return CargaAcademicaResponse(
        id=c.id,
        docente_id=c.docente_id,
        docente_nombre=f"{c.docente.nombre} {c.docente.apellido}",
        asignatura=AsignaturaResponse.from_orm(c.asignatura),
        grupo=GrupoResponse(
            id=c.grupo.id,
            nombre=c.grupo.nombre,
            grado=c.grupo.grado,
            sede=SedeResponse.from_orm(c.grupo.sede),
            director=director_dict
        )
    )

@router.delete("/carga-academica/{carga_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_carga_academica(
    carga_id: uuid.UUID,
    current_user: DirectivoUser,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CargaAcademicaORM).where(CargaAcademicaORM.id == carga_id))
    carga = result.scalars().first()
    if not carga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La carga académica especificada no existe."
        )

    await db.execute(delete(CargaAcademicaORM).where(CargaAcademicaORM.id == carga_id))
    await db.commit()
    return None
