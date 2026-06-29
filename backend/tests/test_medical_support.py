# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import pytest
import uuid
import base64
from datetime import date
from sqlalchemy import select
from app.adapters.db.session import AsyncSessionLocal
from app.adapters.db.models import (
    EstudianteORM,
    EntornoSaludORM,
    GrupoORM,
    UsuarioORM
)
from app.core.portable_exporter import (
    serialize_student_data,
    deserialize_and_import_student
)

@pytest.mark.asyncio
async def test_medical_support_pdf_export_import_cycle():
    async with AsyncSessionLocal() as session:
        try:
            group_stmt = select(GrupoORM).limit(1)
            group_res = await session.execute(group_stmt)
            group = group_res.scalars().first()
            grupo_id = group.id if group else None

            user_stmt = select(UsuarioORM).limit(1)
            user_res = await session.execute(user_stmt)
            user = user_res.scalars().first()
            user_id = user.id if user else None

            unique_doc = "MED-TEST-" + str(uuid.uuid4())[:15]
            student = EstudianteORM(
                nombres="Carlos Support",
                apellidos="Test",
                tipo_documento="TI",
                numero_documento=unique_doc,
                fecha_nacimiento=date(2014, 2, 28),
                edad=12,
                departamento_residencia="Antioquia",
                municipio_residencia="Medellín",
                direccion="Carrera 45 # 26-10",
                barrio_vereda="El Poblado",
                grupo_id=grupo_id,
                creado_por=user_id
            )
            session.add(student)
            await session.flush()

            fake_pdf_content = b"%PDF-1.4 mock medical diagnostic report content here..."
            salud = EntornoSaludORM(
                estudiante_id=student.id,
                afiliacion_salud=True,
                eps="Sura",
                regimen="contributivo",
                tiene_diagnostico_medico=True,
                diagnostico_medico="Autismo Grado 1",
                soporte_medico_nombre="diagnostico_autismo.pdf",
                soporte_medico_archivo=fake_pdf_content,
                consume_medicamentos=False,
                asiste_terapias=False,
                terapias_detalle=[]
            )
            session.add(salud)
            await session.flush()

            serialized_data = await serialize_student_data(session, student.id)

            assert "entorno_salud" in serialized_data
            salud_serialized = serialized_data["entorno_salud"]
            assert salud_serialized["soporte_medico_nombre"] == "diagnostico_autismo.pdf"
            assert "soporte_medico_archivo" in salud_serialized
            b64_content = salud_serialized["soporte_medico_archivo"]
            assert isinstance(b64_content, str)
            decoded_bytes = base64.b64decode(b64_content.encode('utf-8'))
            assert decoded_bytes == fake_pdf_content

            new_doc = "MED-TEST-IMP-" + str(uuid.uuid4())[:10]
            serialized_data["student"]["numero_documento"] = new_doc

            imported_student = await deserialize_and_import_student(
                session, serialized_data, grupo_id, user_id
            )
            await session.flush()

            stmt = select(EstudianteORM).where(EstudianteORM.id == imported_student.id)
            res = await session.execute(stmt)
            student_db = res.scalars().first()

            assert student_db is not None
            assert student_db.entorno_salud is not None
            assert student_db.entorno_salud.tiene_diagnostico_medico is True
            assert student_db.entorno_salud.soporte_medico_nombre == "diagnostico_autismo.pdf"
            assert student_db.entorno_salud.soporte_medico_archivo == fake_pdf_content
        finally:
            await session.rollback()

    from app.adapters.db.session import engine
    await engine.dispose()
