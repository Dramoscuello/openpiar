# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import pytest
import uuid
from datetime import date
from sqlalchemy import select
from app.adapters.db.session import AsyncSessionLocal
from app.adapters.db.models import (
    EstudianteORM,
    EntornoSaludORM,
    PiarORM,
    AjusteRazonableORM,
    PeriodoAcademicoORM,
    GrupoORM
)
from app.core.portable_exporter import (
    encrypt_data,
    decrypt_data,
    serialize_student_data,
    deserialize_and_import_student
)

@pytest.mark.asyncio
async def test_encryption_decryption():
    data = {"hello": "world", "number": 123}
    password = "MySecurePassword123"
    
    # Cifrado
    encrypted_bytes = encrypt_data(data, password)
    assert isinstance(encrypted_bytes, bytes)
    assert encrypted_bytes.startswith(b"OPENPIAR")
    
    # Descifrado
    decrypted_data = decrypt_data(encrypted_bytes, password)
    assert decrypted_data == data
    
    # Descifrado con contraseña incorrecta
    with pytest.raises(ValueError, match="Contraseña incorrecta"):
        decrypt_data(encrypted_bytes, "wrong_password")


@pytest.mark.asyncio
async def test_full_export_import_cycle():
    async with AsyncSessionLocal() as session:
        # Iniciar transacción que será deshecha al finalizar
        # Buscar un grupo existente
        group_stmt = select(GrupoORM).limit(1)
        group_res = await session.execute(group_stmt)
        group = group_res.scalars().first()
        grupo_id = group.id if group else None
        
        # Buscar un periodo activo
        period_stmt = select(PeriodoAcademicoORM).where(PeriodoAcademicoORM.activo == True).limit(1)
        period_res = await session.execute(period_stmt)
        period = period_res.scalars().first()
        periodo_id = period.id if period else None

        # Buscar un usuario real para creado_por (evitar violación de FK)
        from app.adapters.db.models import UsuarioORM
        user_stmt = select(UsuarioORM).limit(1)
        user_res = await session.execute(user_stmt)
        user = user_res.scalars().first()
        user_id = user.id if user else None
        
        # 1. Crear estudiante de pruebas
        unique_doc = "TEST-" + str(uuid.uuid4())[:15]
        student = EstudianteORM(
            nombres="Pedro",
            apellidos="Test",
            tipo_documento="TI",
            numero_documento=unique_doc,
            fecha_nacimiento=date(2012, 10, 5),
            edad=13,
            departamento_residencia="Antioquia",
            municipio_residencia="Medellín",
            direccion="Calle Falsa 123",
            barrio_vereda="Centro",
            grupo_id=grupo_id,
            creado_por=user_id
        )
        session.add(student)
        await session.flush()
        
        # Añadir Entorno Salud
        salud = EntornoSaludORM(
            estudiante_id=student.id,
            afiliacion_salud=True,
            eps="EPS Sura",
            regimen="contributivo",
            tiene_diagnostico_medico=True,
            diagnostico_medico="Hipoacusia leve",
            consume_medicamentos=False,
            asiste_terapias=False,
            terapias_detalle=[]
        )
        session.add(salud)
        
        # Añadir un PIAR
        piar = PiarORM(
            estudiante_id=student.id,
            anio_lectivo=2026,
            estado="borrador",
            docentes_elaboran="Juan Pérez",
            creado_por=user_id
        )
        session.add(piar)
        await session.flush()
        
        # Añadir Ajustes razonables si existe periodo
        if periodo_id:
            ajuste = AjusteRazonableORM(
                piar_id=piar.id,
                periodo_id=periodo_id,
                area="Matemáticas",
                titulo_tema="Fracciones",
                objetivos_propositos="Comprender las fracciones",
                barreras_evidenciadas="Dificultad de lectura",
                ajustes_estrategias="Usar bloques de lego",
                evaluacion_ajustes="Pendiente"
            )
            session.add(ajuste)
            
        await session.flush()
        
        # 2. Serializar
        serialized = await serialize_student_data(session, student.id)
        assert serialized["student"]["numero_documento"] == unique_doc
        assert serialized["entorno_salud"]["diagnostico_medico"] == "Hipoacusia leve"
        if periodo_id:
            assert len(serialized["piars"][0]["ajustes_razonables"]) == 1
            assert serialized["piars"][0]["ajustes_razonables"][0]["area"] == "Matemáticas"
            
        # 3. Cifrar y descifrar
        encrypted = encrypt_data(serialized, "exportpassword")
        decrypted = decrypt_data(encrypted, "exportpassword")
        
        # 4. Importar con otro documento para simular nuevo estudiante en colegio destino
        decrypted["student"]["numero_documento"] = unique_doc + "-IMP"
        
        imported_student = await deserialize_and_import_student(
            session, decrypted, grupo_id, creado_por_id=user_id
        )
        
        assert imported_student.numero_documento == unique_doc + "-IMP"
        assert imported_student.nombres == "Pedro"
        assert imported_student.entorno_salud.diagnostico_medico == "Hipoacusia leve"
        
        # Deshacer cambios
        await session.rollback()

    from app.adapters.db.session import engine
    await engine.dispose()
