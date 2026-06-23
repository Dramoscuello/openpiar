import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import google.generativeai as genai
import os

from app.adapters.db.session import get_db
from app.adapters.db.models import (
    PiarORM,
    CaracteristicasEstudianteORM,
    AjusteRazonableORM,
    PeriodoAcademicoORM,
    EstudianteORM
)
from app.entrypoints.api.schemas import (
    PiarCreate,
    PiarResponse,
    AjusteRazonableCreate,
    AjusteRazonableResponse,
    GenerarAjustesRequest,
    BaseResponse
)

router = APIRouter(prefix="/piars", tags=["piars"])

@router.get("/estudiante/{estudiante_id}", response_model=PiarResponse)
async def get_piar_by_estudiante(estudiante_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Obtiene el PIAR activo para un estudiante, incluyendo características y ajustes."""
    query = (
        select(PiarORM)
        .where(PiarORM.estudiante_id == estudiante_id)
        .options(
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables)
        )
        .order_by(PiarORM.created_at.desc())
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado para este estudiante.")
    
    return piar

@router.post("/", response_model=PiarResponse)
async def create_piar(data: PiarCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo documento PIAR para el estudiante."""
    # Verificar si el estudiante existe
    estudiante = await db.get(EstudianteORM, data.estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    nuevo_piar = PiarORM(
        estudiante_id=data.estudiante_id,
        anio_lectivo=data.anio_lectivo,
        estado=data.estado,
        docentes_elaboran=data.docentes_elaboran
    )
    db.add(nuevo_piar)
    await db.commit()
    await db.refresh(nuevo_piar)
    return nuevo_piar

@router.post("/{piar_id}/ajustes", response_model=AjusteRazonableResponse)
async def add_ajuste_razonable(piar_id: uuid.UUID, data: AjusteRazonableCreate, db: AsyncSession = Depends(get_db)):
    """Agrega un ajuste razonable a un PIAR asociándolo al periodo académico activo."""
    # Verificar si el PIAR existe
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    # Buscar el periodo activo
    periodo_query = select(PeriodoAcademicoORM).where(PeriodoAcademicoORM.activo == True)
    result = await db.execute(periodo_query)
    periodo_activo = result.scalars().first()

    if not periodo_activo:
        raise HTTPException(status_code=400, detail="No hay ningún periodo académico activo. Active uno en Gestión Escolar.")

    nuevo_ajuste = AjusteRazonableORM(
        piar_id=piar_id,
        periodo_id=periodo_activo.id,
        area=data.area,
        objetivos_propositos=data.objetivos_propositos,
        barreras_evidenciadas=data.barreras_evidenciadas,
        ajustes_estrategias=data.ajustes_estrategias,
        evaluacion_ajustes=data.evaluacion_ajustes
    )
    db.add(nuevo_ajuste)
    await db.commit()
    await db.refresh(nuevo_ajuste)
    return nuevo_ajuste

@router.post("/{piar_id}/generar_ia")
async def generar_ajustes_ia(piar_id: uuid.UUID, data: GenerarAjustesRequest, db: AsyncSession = Depends(get_db)):
    """Genera recomendaciones DUA usando Google Gemini."""
    try:
        # Verificar PIAR
        piar = await db.get(PiarORM, piar_id)
        if not piar:
            raise HTTPException(status_code=404, detail="PIAR no encontrado.")

        # Construir Prompt
        prompt = (
            f"Actúa como un experto en Educación Inclusiva y Diseño Universal para el Aprendizaje (DUA).\n"
            f"Necesito sugerencias de estrategias y ajustes razonables concretos para un estudiante.\n\n"
            f"Contexto:\n"
            f"- Área/Materia: {data.area}\n"
            f"- Objetivos o Propósitos de Aprendizaje: {data.objetivos_propositos}\n"
            f"- Barreras Evidenciadas en el Estudiante: {data.barreras_evidenciadas}\n"
        )
        if data.instrucciones_adicionales:
            prompt += f"\nInstrucciones adicionales del docente: {data.instrucciones_adicionales}\n"
        
        prompt += (
            "\nEscribe ÚNICAMENTE las estrategias DUA propuestas en un formato claro, accionable y "
            "directo, sin preámbulos, organizadas en viñetas o un párrafo claro."
        )

        # Usar la librería google-generativeai
        # Asegurarse de tener GEMINI_API_KEY en las variables de entorno
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return {"success": True, "estrategias_generadas": response.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando IA: {str(e)}")
