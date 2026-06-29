# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints del Directorio de padres y acudientes.
Ruta: /api/v1/directorio/

Accesible solo para directivo o director de grupo.
Muestra solo el acudiente principal por estudiante,
con opción de compartir el PDF del acta de acuerdo.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import EntornoHogarORM, EstudianteORM, GrupoORM, GradoORM, PiarORM
from app.adapters.db.session import get_db
from app.entrypoints.api.dependencies import CurrentUser
from app.entrypoints.api.schemas import (
    ContactoDirectorioOut,
    DirectorioResponse,
    EstudianteDirectorioOut,
)

router = APIRouter(prefix="/directorio", tags=["directorio"])


def _piar_activo_id(piars: list) -> Optional[str]:
    for p in piars:
        if p.estado != "vencido":
            return str(p.id)
    if piars:
        return str(piars[-1].id)
    return None


def _resolver_acudiente(hogar: EntornoHogarORM) -> Optional[dict]:
    acudiente = hogar.acudiente_principal

    if acudiente == "madre" and hogar.nombre_madre and hogar.nombre_madre.strip():
        return {
            "nombre": hogar.nombre_madre.strip(),
            "rol": "madre",
            "telefono": hogar.telefono_madre,
            "correo": hogar.correo_madre,
            "numero_documento": hogar.numero_documento_madre.strip() if hogar.numero_documento_madre else None,
            "acudiente_principal": True,
        }

    if acudiente == "padre" and hogar.nombre_padre and hogar.nombre_padre.strip():
        return {
            "nombre": hogar.nombre_padre.strip(),
            "rol": "padre",
            "telefono": hogar.telefono_padre,
            "correo": hogar.correo_padre,
            "numero_documento": hogar.numero_documento_padre.strip() if hogar.numero_documento_padre else None,
            "acudiente_principal": True,
        }

    if acudiente == "cuidador" and hogar.nombre_cuidador and hogar.nombre_cuidador.strip():
        return {
            "nombre": hogar.nombre_cuidador.strip(),
            "rol": "cuidador",
            "telefono": hogar.telefono_cuidador,
            "correo": hogar.correo_cuidador,
            "numero_documento": None,
            "acudiente_principal": True,
        }

    if hogar.nombre_cuidador and hogar.nombre_cuidador.strip():
        return {
            "nombre": hogar.nombre_cuidador.strip(),
            "rol": "cuidador",
            "telefono": hogar.telefono_cuidador,
            "correo": hogar.correo_cuidador,
            "numero_documento": None,
            "acudiente_principal": True,
        }

    if hogar.nombre_madre and hogar.nombre_madre.strip():
        return {
            "nombre": hogar.nombre_madre.strip(),
            "rol": "madre",
            "telefono": hogar.telefono_madre,
            "correo": hogar.correo_madre,
            "numero_documento": hogar.numero_documento_madre.strip() if hogar.numero_documento_madre else None,
            "acudiente_principal": False,
        }

    if hogar.nombre_padre and hogar.nombre_padre.strip():
        return {
            "nombre": hogar.nombre_padre.strip(),
            "rol": "padre",
            "telefono": hogar.telefono_padre,
            "correo": hogar.correo_padre,
            "numero_documento": hogar.numero_documento_padre.strip() if hogar.numero_documento_padre else None,
            "acudiente_principal": False,
        }

    return None


def _find_existing(
    contactos: list[dict],
    nombre: str,
    rol: str,
    numero_documento: Optional[str],
) -> Optional[dict]:
    if numero_documento:
        for c in contactos:
            if c["numero_documento"] == numero_documento and c["rol"] == rol:
                return c
    for c in contactos:
        if c["nombre"].lower() == nombre.lower() and c["rol"] == rol:
            return c
    return None


@router.get(
    "",
    response_model=DirectorioResponse,
    summary="Listar contactos del directorio",
)
async def listar_directorio(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DirectorioResponse:
    es_directivo = current_user.rol.es_directivo

    if not es_directivo:
        group_result = await db.execute(
            select(GrupoORM).where(GrupoORM.director_id == current_user.id)
        )
        if group_result.scalars().first() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo directivos o directores de grupo pueden acceder al directorio.",
            )

    # Auto-marcar PIARs vencidos
    hoy = date.today()
    await db.execute(
        update(PiarORM)
        .where(
            PiarORM.estado.notin_(["firmado", "vencido"]),
            PiarORM.fecha_limite_firma.isnot(None),
            PiarORM.fecha_limite_firma < hoy,
        )
        .values(estado="vencido")
    )
    await db.commit()

    result = await db.execute(
        select(EntornoHogarORM).options(
            selectinload(EntornoHogarORM.estudiante)
            .selectinload(EstudianteORM.grupo)
            .selectinload(GrupoORM.grado),
            selectinload(EntornoHogarORM.estudiante)
            .selectinload(EstudianteORM.piars),
        )
    )
    hogares = result.scalars().all()

    contactos: list[dict] = []

    for h in hogares:
        estudiante = h.estudiante
        if not estudiante:
            continue

        acudiente_data = _resolver_acudiente(h)
        if not acudiente_data:
            continue

        estudiante_entry = EstudianteDirectorioOut(
            id=estudiante.id,
            nombre=f"{estudiante.nombres} {estudiante.apellidos}",
            grado=estudiante.grupo.grado.nombre if estudiante.grupo and estudiante.grupo.grado else None,
            piar_id=_piar_activo_id(estudiante.piars),
        )

        existing = _find_existing(
            contactos,
            acudiente_data["nombre"],
            acudiente_data["rol"],
            acudiente_data.get("numero_documento"),
        )
        if existing:
            existing["estudiantes"].append(estudiante_entry)
        else:
            acudiente_data["estudiantes"] = [estudiante_entry]
            contactos.append(acudiente_data)

    contactos_out = [ContactoDirectorioOut(**c) for c in contactos]
    return DirectorioResponse(contactos=contactos_out)
