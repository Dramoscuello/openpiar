# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Caso de uso: Crear Estudiante.

Orquesta la lógica de negocio para registrar un nuevo estudiante
beneficiario del PIAR. Valida que no exista un duplicado por documento.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.core.exceptions import EstudianteYaRegistradoError
from app.domain.entities import Estudiante
from app.domain.ports import IEstudianteRepository


@dataclass
class CrearEstudianteInput:
    """DTO de entrada para el caso de uso."""
    nombres: str
    apellidos: str
    tipo_documento: str
    numero_documento: str
    fecha_nacimiento: date
    edad: int
    departamento_residencia: str
    municipio_residencia: str
    direccion: str
    barrio_vereda: str
    creado_por: Optional[uuid.UUID] = None
    lugar_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    en_centro_proteccion: bool = False
    centro_proteccion_donde: Optional[str] = None
    grupo_etnico: Optional[str] = None
    victima_conflicto: bool = False
    registro_victima: bool = False


class CrearEstudianteUseCase:
    """
    Caso de uso: registrar un nuevo estudiante en el sistema.

    Reglas de negocio:
    - El número de documento (tipo + número) debe ser único en el sistema.
    - La edad debe ser consistente (>= 0).
    - El creador debe ser un usuario registrado.
    """

    def __init__(self, estudiante_repository: IEstudianteRepository) -> None:
        # Inyecta la abstracción, no la implementación concreta
        self._repo = estudiante_repository

    async def execute(self, data: CrearEstudianteInput) -> Estudiante:
        """
        Ejecuta el registro del estudiante.

        Raises:
            EstudianteYaRegistradoError: Si ya existe un estudiante con ese documento.
            ValueError: Si los datos violan invariantes del dominio.
        """
        # Verificar unicidad de documento
        existente = await self._repo.find_by_documento(
            data.tipo_documento, data.numero_documento
        )
        if existente:
            raise EstudianteYaRegistradoError(
                f"Ya existe un estudiante registrado con el documento "
                f"{data.tipo_documento} {data.numero_documento}."
            )

        # Crear entidad de dominio (valida invariantes)
        estudiante = Estudiante.crear(
            nombres=data.nombres,
            apellidos=data.apellidos,
            tipo_documento=data.tipo_documento,
            numero_documento=data.numero_documento,
            fecha_nacimiento=data.fecha_nacimiento,
            edad=data.edad,
            departamento_residencia=data.departamento_residencia,
            municipio_residencia=data.municipio_residencia,
            direccion=data.direccion,
            barrio_vereda=data.barrio_vereda,
            creado_por=data.creado_por,
            lugar_nacimiento=data.lugar_nacimiento,
            telefono=data.telefono,
            correo=data.correo,
            en_centro_proteccion=data.en_centro_proteccion,
            centro_proteccion_donde=data.centro_proteccion_donde,
            grupo_etnico=data.grupo_etnico,
            victima_conflicto=data.victima_conflicto,
            registro_victima=data.registro_victima,
        )

        return await self._repo.save(estudiante)
