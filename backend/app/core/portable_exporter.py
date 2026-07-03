# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import os
import json
import uuid
from datetime import date, datetime
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.adapters.db.models import (
    EstudianteORM,
    EntornoSaludORM,
    EntornoHogarORM,
    TrayectoriaEducativaORM,
    MatriculaActualORM,
)

def encrypt_data(data: dict, password: str) -> bytes:
    """
    Serializa un diccionario a JSON y lo cifra usando AES-256-GCM.
    La clave se deriva de la contraseña ingresada mediante PBKDF2-HMAC-SHA256.
    """
    json_bytes = json.dumps(data, default=str).encode('utf-8')
    
    salt = os.urandom(16)
    nonce = os.urandom(12)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode('utf-8'))
    
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, json_bytes, None)
    
    # Empaquetar formato .openpiar: cabecera mágica (8 bytes) + sal (16) + nonce (12) + datos
    return b"OPENPIAR" + salt + nonce + ciphertext


def decrypt_data(encrypted_bytes: bytes, password: str) -> dict:
    """
    Desempaqueta un archivo .openpiar, valida su cabecera y descifra el payload JSON usando AES-256-GCM.
    """
    if len(encrypted_bytes) < 36:
        raise ValueError("Archivo inválido o demasiado corto.")
        
    if not encrypted_bytes.startswith(b"OPENPIAR"):
        raise ValueError("Cabecera de archivo inválida. No es un archivo .openpiar válido.")
        
    salt = encrypted_bytes[8:24]
    nonce = encrypted_bytes[24:36]
    ciphertext = encrypted_bytes[36:]
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode('utf-8'))
    
    aesgcm = AESGCM(key)
    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Contraseña incorrecta o archivo corrompido.")
        
    return json.loads(decrypted_bytes.decode('utf-8'))


def model_to_dict(instance, exclude_fields=None) -> Optional[dict]:
    """
    Helper genérico para convertir un modelo SQLAlchemy a diccionario,
    excluyendo las llaves primarias/foráneas locales y marcas de tiempo del sistema.
    """
    if not instance:
        return None
        
    if exclude_fields is None:
        exclude_fields = {"id", "created_at", "updated_at", "creado_por", "grupo_id", "piar_id", "estudiante_id", "acta_id"}
        
    res = {}
    for col in instance.__table__.columns:
        if col.name not in exclude_fields:
            val = getattr(instance, col.name)
            if isinstance(val, (date, datetime)):
                res[col.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                res[col.name] = str(val)
            elif isinstance(val, bytes):
                import base64
                res[col.name] = base64.b64encode(val).decode('utf-8')
            else:
                res[col.name] = val
    return res


def populate_orm(model_class, data_dict: dict, **kwargs) -> Any:
    """
    Instancia un modelo SQLAlchemy poblando sus columnas a partir del diccionario,
    realizando la conversión de tipos necesaria (fechas/horas desde texto).
    """
    if not data_dict:
        return None
        
    clean_dict = {}
    for k, v in data_dict.items():
        col = model_class.__table__.columns.get(k)
        if col is not None and v is not None:
            from sqlalchemy import Date, DateTime, LargeBinary
            if isinstance(col.type, Date) and isinstance(v, str):
                clean_dict[k] = date.fromisoformat(v)
            elif isinstance(col.type, DateTime) and isinstance(v, str):
                clean_dict[k] = datetime.fromisoformat(v)
            elif isinstance(col.type, LargeBinary) and isinstance(v, str):
                import base64
                clean_dict[k] = base64.b64decode(v.encode('utf-8'))
            else:
                clean_dict[k] = v
        else:
            clean_dict[k] = v
            
    for k, v in kwargs.items():
        clean_dict[k] = v
        
    return model_class(**clean_dict)


async def serialize_student_data(db: AsyncSession, estudiante_id: uuid.UUID) -> dict:
    """
    Consulta toda la información y relaciones del estudiante en la base de datos
    y construye el grafo de datos JSON para la exportación.
    """
    stmt = (
        select(EstudianteORM)
        .where(EstudianteORM.id == estudiante_id)
        .options(
            selectinload(EstudianteORM.entorno_salud),
            selectinload(EstudianteORM.entorno_hogar),
            selectinload(EstudianteORM.trayectoria_educativa),
            selectinload(EstudianteORM.matricula_actual),
        )
    )
    res = await db.execute(stmt)
    estudiante = res.scalars().first()
    if not estudiante:
        raise ValueError("Estudiante no encontrado en la base de datos.")
        
    export_payload = {
        "version": "1.0",
        "student": model_to_dict(estudiante),
        "entorno_salud": model_to_dict(estudiante.entorno_salud),
        "entorno_hogar": model_to_dict(estudiante.entorno_hogar),
        "trayectoria_educativa": model_to_dict(estudiante.trayectoria_educativa),
        "matricula_actual": model_to_dict(estudiante.matricula_actual),
    }

    return export_payload


async def deserialize_and_import_student(
    db: AsyncSession, data: dict, grupo_id: Optional[uuid.UUID], creado_por_id: uuid.UUID
) -> EstudianteORM:
    """
    Importa la información deserializada de un estudiante.
    Si el estudiante ya existe en la base de datos de destino, actualiza sus datos y anexa
    su historial académico e instrumental de PIAR, recreando sus relaciones adecuadamente.
    """
    student_data = data.get("student")
    if not student_data:
        raise ValueError("Datos del estudiante ausentes en el archivo .openpiar.")
        
    num_doc = student_data.get("numero_documento")
    tipo_doc = student_data.get("tipo_documento")
    
    # 1. Comprobar si el estudiante ya existe
    stmt = (
        select(EstudianteORM)
        .where(
            (EstudianteORM.numero_documento == num_doc) & 
            (EstudianteORM.tipo_documento == tipo_doc)
        )
        .options(
            selectinload(EstudianteORM.entorno_salud),
            selectinload(EstudianteORM.entorno_hogar),
            selectinload(EstudianteORM.trayectoria_educativa),
            selectinload(EstudianteORM.matricula_actual),
        )
    )
    res = await db.execute(stmt)
    estudiante = res.scalars().first()
    
    is_new = False
    if estudiante:
        # Actualizar campos del estudiante existente
        for k, v in student_data.items():
            if k not in {"id", "created_at", "updated_at", "creado_por"}:
                setattr(estudiante, k, v)
        if grupo_id:
            estudiante.grupo_id = grupo_id
    else:
        # Crear estudiante nuevo
        estudiante = populate_orm(
            EstudianteORM, student_data, grupo_id=grupo_id, creado_por=creado_por_id
        )
        db.add(estudiante)
        is_new = True
        
    await db.flush()  # Confirmar existencia u obtención del ID del estudiante
    
    # 2. Recrear entornos
    # Entorno Salud
    if not is_new and estudiante.entorno_salud:
        await db.delete(estudiante.entorno_salud)
    salud_data = data.get("entorno_salud")
    if salud_data:
        estudiante.entorno_salud = populate_orm(EntornoSaludORM, salud_data, estudiante_id=estudiante.id)
        
    # Entorno Hogar
    if not is_new and estudiante.entorno_hogar:
        await db.delete(estudiante.entorno_hogar)
    hogar_data = data.get("entorno_hogar")
    if hogar_data:
        estudiante.entorno_hogar = populate_orm(EntornoHogarORM, hogar_data, estudiante_id=estudiante.id)
        
    # Trayectoria Educativa
    if not is_new and estudiante.trayectoria_educativa:
        await db.delete(estudiante.trayectoria_educativa)
    trayectoria_data = data.get("trayectoria_educativa")
    if trayectoria_data:
        estudiante.trayectoria_educativa = populate_orm(TrayectoriaEducativaORM, trayectoria_data, estudiante_id=estudiante.id)
        
    # Matrícula Actual
    if not is_new and estudiante.matricula_actual:
        await db.delete(estudiante.matricula_actual)
    matricula_data = data.get("matricula_actual")
    if matricula_data:
        estudiante.matricula_actual = populate_orm(MatriculaActualORM, matricula_data, estudiante_id=estudiante.id)
        
    await db.flush()

    await db.commit()
    return estudiante
