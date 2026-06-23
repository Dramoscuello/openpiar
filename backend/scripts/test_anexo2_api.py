import asyncio
import uuid
from datetime import date
import httpx
import sys
import os

# Asegurar path correcto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.adapters.db.session import AsyncSessionLocal
from app.adapters.db.models import (
    SedeORM,
    GrupoORM,
    EstudianteORM,
    PeriodoAcademicoORM,
    PiarORM,
    AjusteRazonableORM,
    RecomendacionPMIORM,
    UsuarioORM
)
from app.core.security import get_password_hash, create_access_token

async def test_anexo2_api_flow():
    # Identificadores de prueba
    sede_id = uuid.uuid4()
    grupo_id = uuid.uuid4()
    estudiante_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    piar_id = None
    ajuste_id = None
    pmi_id = None
    periodo_id = None
    token = None

    print("--- INICIANDO PRUEBA DE INTEGRACIÓN DE ANEXO 2 ---")

    try:
        # 1. Configurar datos semilla en la BD
        async with AsyncSessionLocal() as session:
            sede = SedeORM(
                id=sede_id,
                nombre="Sede Anexo2 Test",
                direccion="Calle Test",
                telefono="111"
            )
            session.add(sede)

            grupo = GrupoORM(
                id=grupo_id,
                nombre="Grupo Anexo2 Test",
                grado="5",
                sede_id=sede_id
            )
            session.add(grupo)

            estudiante = EstudianteORM(
                id=estudiante_id,
                nombres="Julio",
                apellidos="Cortazar",
                tipo_documento="TI",
                numero_documento=f"an2_test_{uuid.uuid4().hex[:6]}",
                fecha_nacimiento=date(2011, 2, 12),
                edad=15,
                departamento_residencia="Cundinamarca",
                municipio_residencia="Bogota",
                direccion="Calle Falsa 123",
                barrio_vereda="Teusaquillo",
                grupo_id=grupo_id
            )
            session.add(estudiante)

            # Crear periodo académico activo
            periodo = PeriodoAcademicoORM(
                nombre="Periodo Anexo2 Test",
                activo=True,
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 12, 31)
            )
            session.add(periodo)

            # Crear usuario para autenticación
            email = f"an2_test_user_{uuid.uuid4().hex[:6]}@example.com"
            usuario = UsuarioORM(
                id=usuario_id,
                email=email,
                password_hash=get_password_hash("password123"),
                nombre="Profesor",
                apellido="Jirafales",
                rol="docente_apoyo"
            )
            session.add(usuario)

            await session.commit()
            periodo_id = periodo.id
            token = create_access_token(str(usuario_id))
            print(f"1. Semillas insertadas correctamente. Periodo ID: {periodo_id}, Usuario ID: {usuario_id}")

        # 2. Probar API usando AsyncClient
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers=headers
        ) as client:
            # A. Crear PIAR
            resp = await client.post("/api/v1/piars/", json={
                "estudiante_id": str(estudiante_id),
                "anio_lectivo": 2026,
                "estado": "borrador",
                "docentes_elaboran": "Profesor Jirafales"
            })
            assert resp.status_code == 200, f"Error creando PIAR: {resp.text}"
            piar_data = resp.json()
            piar_id = uuid.UUID(piar_data["id"])
            print(f"A. PIAR creado con ID: {piar_id}")

            # B. Obtener PIAR de estudiante
            resp = await client.get(f"/api/v1/piars/estudiante/{estudiante_id}")
            assert resp.status_code == 200, f"Error obteniendo PIAR: {resp.text}"
            assert resp.json()["id"] == str(piar_id)
            print("B. GET PIAR por estudiante funciona y retorna el ID correcto.")

            # C. PATCH /piars/{piar_id} para actualizar Características del Estudiante
            resp = await client.patch(f"/api/v1/piars/{piar_id}", json={
                "docentes_elaboran": "Profesor Jirafales, Director Sarmiento",
                "caracteristicas": {
                    "descripcion_gustos_intereses": "Le gusta leer cronopios y jugar ajedrez.",
                    "descripcion_habilidades": "Excelente redacción, requiere apoyo en matemáticas visuales."
                }
            })
            assert resp.status_code == 200, f"Error actualizando características: {resp.text}"
            data_actualizada = resp.json()
            assert data_actualizada["docentes_elaboran"] == "Profesor Jirafales, Director Sarmiento"
            assert data_actualizada["caracteristicas"] is not None
            assert data_actualizada["caracteristicas"]["descripcion_gustos_intereses"] == "Le gusta leer cronopios y jugar ajedrez."
            print("C. PATCH PIAR y Características del Estudiante funciona correctamente.")

            # D. POST /piars/{piar_id}/ajustes para agregar Ajuste Razonable
            resp = await client.post(f"/api/v1/piars/{piar_id}/ajustes", json={
                "area": "Matemáticas",
                "objetivos_propositos": "DBA 2: Resolver operaciones combinadas.",
                "barreras_evidenciadas": "Falta de comprensión de enunciados largos.",
                "ajustes_estrategias": "Simplificación verbal de enunciados y uso de material didáctico.",
                "evaluacion_ajustes": ""
            })
            assert resp.status_code == 200, f"Error creando ajuste razonable: {resp.text}"
            ajuste_data = resp.json()
            ajuste_id = uuid.UUID(ajuste_data["id"])
            print(f"D. Ajuste razonable creado con ID: {ajuste_id}")

            # E. PUT /piars/{piar_id}/ajustes/{ajuste_id} para actualizar el ajuste
            resp = await client.put(f"/api/v1/piars/{piar_id}/ajustes/{ajuste_id}", json={
                "area": "Matemáticas",
                "objetivos_propositos": "DBA 2: Resolver operaciones combinadas de suma y resta.",
                "barreras_evidenciadas": "Falta de comprensión de enunciados extensos y complejos.",
                "ajustes_estrategias": "Estrategias DUA de simplificación.",
                "evaluacion_ajustes": "Se observa mejora al final del periodo."
            })
            assert resp.status_code == 200, f"Error editando ajuste: {resp.text}"
            assert resp.json()["evaluacion_ajustes"] == "Se observa mejora al final del periodo."
            print("E. PUT Ajuste Razonable funciona correctamente.")

            # F. POST /piars/{piar_id}/pmi para agregar Recomendación PMI
            resp = await client.post(f"/api/v1/piars/{piar_id}/pmi", json={
                "actor": "Docentes",
                "acciones": "Capacitación en DUA.",
                "estrategias_implementar": "Talleres semanales pedagógicos."
            })
            assert resp.status_code == 200, f"Error creando recomendación PMI: {resp.text}"
            pmi_data = resp.json()
            pmi_id = uuid.UUID(pmi_data["id"])
            print(f"F. Recomendación PMI creada con ID: {pmi_id}")

            # G. PUT /piars/{piar_id}/pmi/{pmi_id} para actualizar recomendación
            resp = await client.put(f"/api/v1/piars/{piar_id}/pmi/{pmi_id}", json={
                "actor": "Docentes",
                "acciones": "Capacitación en DUA y TEAp.",
                "estrategias_implementar": "Talleres mensuales de 2 horas."
            })
            assert resp.status_code == 200, f"Error editando recomendación PMI: {resp.text}"
            assert resp.json()["acciones"] == "Capacitación en DUA y TEAp."
            print("G. PUT Recomendación PMI funciona correctamente.")

            # H. Obtener PIAR completo nuevamente para validar relaciones jerárquicas
            resp = await client.get(f"/api/v1/piars/estudiante/{estudiante_id}")
            assert resp.status_code == 200, f"Error consultando PIAR: {resp.text}"
            full_data = resp.json()
            assert len(full_data["ajustes_razonables"]) == 1
            assert len(full_data["recomendaciones_pmi"]) == 1
            assert full_data["recomendaciones_pmi"][0]["acciones"] == "Capacitación en DUA y TEAp."
            print("H. GET PIAR por estudiante retorna correctamente las relaciones anidadas.")

            # I. DELETE Ajuste razonable
            resp = await client.delete(f"/api/v1/piars/{piar_id}/ajustes/{ajuste_id}")
            assert resp.status_code == 204, f"Error eliminando ajuste: {resp.text}"
            print("I. DELETE Ajuste Razonable funciona correctamente.")

            # J. DELETE Recomendación PMI
            resp = await client.delete(f"/api/v1/piars/{piar_id}/pmi/{pmi_id}")
            assert resp.status_code == 204, f"Error eliminando recomendación: {resp.text}"
            print("J. DELETE Recomendación PMI funciona correctamente.")

            # K. Verificar PIAR vacío
            resp = await client.get(f"/api/v1/piars/estudiante/{estudiante_id}")
            assert resp.status_code == 200
            assert len(resp.json()["ajustes_razonables"]) == 0
            assert len(resp.json()["recomendaciones_pmi"]) == 0
            print("K. Verificación post-eliminación exitosa: Ajustes y PMI vacíos.")

    finally:
        # 3. Limpieza en la BD
        async with AsyncSessionLocal() as session:
            if piar_id:
                piar = await session.get(PiarORM, piar_id)
                if piar:
                    await session.delete(piar)
            
            if periodo_id:
                periodo = await session.get(PeriodoAcademicoORM, periodo_id)
                if periodo:
                    await session.delete(periodo)

            estudiante = await session.get(EstudianteORM, estudiante_id)
            if estudiante:
                await session.delete(estudiante)

            grupo = await session.get(GrupoORM, grupo_id)
            if grupo:
                await session.delete(grupo)

            sede = await session.get(SedeORM, sede_id)
            if sede:
                await session.delete(sede)

            if usuario_id:
                usuario = await session.get(UsuarioORM, usuario_id)
                if usuario:
                    await session.delete(usuario)

            await session.commit()
            print("3. Limpieza de base de datos exitosa.")
            print("--- PRUEBA COMPLETADA EXITOSAMENTE! ---")

if __name__ == "__main__":
    asyncio.run(test_anexo2_api_flow())
