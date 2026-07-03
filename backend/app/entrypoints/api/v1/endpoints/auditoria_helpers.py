# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Helper para registrar automáticamente entradas de auditoría en los endpoints
de PIAR. Centraliza la lógica de logging para mantener limpios los endpoints.

Uso desde un endpoint:
    from app.entrypoints.api.v1.endpoints.auditoria_helpers import (
        registrar_cambio, serializar_ajuste, serializar_pmi,
        serializar_acta, serializar_caracteristicas,
    )

    # Antes del cambio:
    datos_antes = serializar_ajuste(ajuste)

    # ... hacer el cambio (db.commit) ...

    # Después del cambio:
    await registrar_cambio(
        db=db,
        entidad_tipo="ajuste_razonable",
        entidad_id=ajuste.id,
        piar_id=piar_id,
        accion="modificar",
        usuario_id=current_user.id,
        datos_anteriores=datos_antes,
        datos_nuevos=serializar_ajuste(ajuste),
    )
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    AjusteRazonableORM,
    ActaAcuerdoORM,
    CaracteristicasEstudianteORM,
    CompromisoCasaORM,
    RecomendacionPMIORM,
)
from app.adapters.db.postgres.auditoria_repository import (
    PostgresAuditoriaRepository,
)
from app.domain.entities import AuditoriaCambio


def serializar_ajuste(ajuste: AjusteRazonableORM) -> dict:
    return {
        "area": ajuste.area,
        "titulo_tema": ajuste.titulo_tema,
        "objetivos_propositos": ajuste.objetivos_propositos,
        "barreras_evidenciadas": ajuste.barreras_evidenciadas,
        "ajustes_estrategias": ajuste.ajustes_estrategias,
        "evaluacion_ajustes": ajuste.evaluacion_ajustes,
        "puntuacion": ajuste.puntuacion,
        "comentario_puntuacion": ajuste.comentario_puntuacion,
    }


def serializar_pmi(pmi: RecomendacionPMIORM) -> dict:
    return {
        "actor": pmi.actor,
        "acciones": pmi.acciones,
        "estrategias_implementar": pmi.estrategias_implementar,
    }


def serializar_acta(acta: ActaAcuerdoORM) -> dict:
    return {
        "fecha_firma": str(acta.fecha_firma) if acta.fecha_firma else None,
        "compromisos_aula": acta.compromisos_aula,
        "firmado_estudiante": acta.firmado_estudiante,
        "firmado_acudiente": acta.firmado_acudiente,
        "firmado_docente_apoyo": acta.firmado_docente_apoyo,
        "firmado_docentes_aula": acta.firmado_docentes_aula,
        "firmado_directivo": acta.firmado_directivo,
        "compromisos_casa": [
            {
                "nombre_actividad": c.nombre_actividad,
                "descripcion_estrategia": c.descripcion_estrategia,
                "frecuencia": c.frecuencia,
            }
            for c in (acta.compromisos_casa or [])
        ],
    }


def serializar_caracteristicas(caract: CaracteristicasEstudianteORM) -> dict:
    return {
        "descripcion_gustos_intereses": caract.descripcion_gustos_intereses,
        "descripcion_habilidades": caract.descripcion_habilidades,
    }


def serializar_estado_piar(estado: str) -> dict:
    return {"estado": estado}


async def registrar_cambio(
    db: AsyncSession,
    entidad_tipo: str,
    entidad_id: uuid.UUID,
    piar_id: uuid.UUID,
    accion: str,
    usuario_id: uuid.UUID,
    datos_anteriores: Optional[dict] = None,
    datos_nuevos: Optional[dict] = None,
) -> None:
    entrada = AuditoriaCambio.crear(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        piar_id=piar_id,
        accion=accion,
        usuario_id=usuario_id,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
    )
    repo = PostgresAuditoriaRepository(db)
    await repo.save(entrada)
