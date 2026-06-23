import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import google.generativeai as genai

from app.core.config import get_settings
from app.adapters.db.session import get_db
from app.adapters.db.models import (
    PiarORM,
    CaracteristicasEstudianteORM,
    AjusteRazonableORM,
    PeriodoAcademicoORM,
    EstudianteORM,
    RecomendacionPMIORM,
    ConfiguracionSistemaORM
)
from app.entrypoints.api.schemas import (
    PiarCreate,
    PiarUpdate,
    PiarResponse,
    AjusteRazonableCreate,
    AjusteRazonableResponse,
    GenerarAjustesRequest,
    GenerarPlanCompletoRequest,
    PlanCompletoIAResponse,
    BaseResponse,
    RecomendacionPMICreate,
    RecomendacionPMIResponse
)
from app.entrypoints.api.dependencies import CurrentUser

router = APIRouter(prefix="/piars", tags=["piars"])
settings = get_settings()


async def get_gemini_key(db: AsyncSession) -> str:
    """
    Obtiene la clave de API de Gemini con prioridad BD > .env.

    Flujo:
    1. Busca en configuracion_sistema (guardada por el wizard del usuario final).
    2. Si no existe o es nula, usa el valor de GEMINI_API_KEY en .env
       (util para desarrollo local).
    3. Si ninguna está disponible, lanza HTTPException 400.
    """
    result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = result.scalars().first()
    if config and config.gemini_api_key:
        return config.gemini_api_key
    if settings.GEMINI_API_KEY:
        return settings.GEMINI_API_KEY
    raise HTTPException(
        status_code=400,
        detail=(
            "No se encontró la clave de API de Gemini. "
            "Confígurela en el wizard de configuración o en el archivo .env."
        ),
    )

@router.get("/estudiante/{estudiante_id}", response_model=PiarResponse)
async def get_piar_by_estudiante(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el PIAR activo para un estudiante, incluyendo características, ajustes y recomendaciones PMI."""
    query = (
        select(PiarORM)
        .where(PiarORM.estudiante_id == estudiante_id)
        .options(
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables),
            selectinload(PiarORM.recomendaciones_pmi)
        )
        .order_by(PiarORM.created_at.desc())
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado para este estudiante.")
    
    return piar

@router.post("/", response_model=PiarResponse)
async def create_piar(
    data: PiarCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo documento PIAR para el estudiante."""
    # Verificar si el estudiante existe
    estudiante = await db.get(EstudianteORM, data.estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    docentes = f"{current_user.nombre} {current_user.apellido}"
    nuevo_piar = PiarORM(
        estudiante_id=data.estudiante_id,
        anio_lectivo=data.anio_lectivo,
        estado=data.estado,
        creado_por=current_user.id,
        docentes_elaboran=docentes
    )
    db.add(nuevo_piar)
    await db.commit()
    
    # Consultar el PIAR recién creado cargando todas sus relaciones para la respuesta
    query = (
        select(PiarORM)
        .where(PiarORM.id == nuevo_piar.id)
        .options(
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables),
            selectinload(PiarORM.recomendaciones_pmi)
        )
    )
    result = await db.execute(query)
    return result.scalars().first()

@router.post("/{piar_id}/ajustes", response_model=AjusteRazonableResponse)
async def add_ajuste_razonable(
    piar_id: uuid.UUID,
    data: AjusteRazonableCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
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
async def generar_ajustes_ia(
    piar_id: uuid.UUID,
    data: GenerarAjustesRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
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

        # Obtener clave Gemini: BD primero, .env como fallback
        gemini_key = await get_gemini_key(db)
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        
        return {"success": True, "estrategias_generadas": response.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando IA: {str(e)}")


@router.post("/{piar_id}/generar_plan_ia", response_model=PlanCompletoIAResponse)
async def generar_plan_completo_ia(
    piar_id: uuid.UUID,
    data: GenerarPlanCompletoRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Genera un plan completo de ajuste razonable por área usando Gemini con todo el contexto del estudiante."""
    try:
        # Verificar PIAR
        piar = await db.get(PiarORM, piar_id)
        if not piar:
            raise HTTPException(status_code=404, detail="PIAR no encontrado.")

        # Construir contexto completo
        contexto_estudiante = f"- Nombre: {data.estudiante_nombre}\n"
        if data.grado:
            contexto_estudiante += f"- Grado escolar: {data.grado}\n"
        if data.diagnostico_medico:
            contexto_estudiante += f"- Diagnóstico médico: {data.diagnostico_medico}\n"
        if data.gustos_intereses:
            contexto_estudiante += f"- Gustos, intereses y expectativas: {data.gustos_intereses}\n"
        if data.habilidades_fortalezas:
            contexto_estudiante += f"- Habilidades, fortalezas y apoyos requeridos: {data.habilidades_fortalezas}\n"

        contexto_curricular = f""
        if data.dba_referencia:
            contexto_curricular += f"\nDerechos Básicos de Aprendizaje (DBA) de referencia para el grado:\n{data.dba_referencia}\n"
        if data.ebc_referencia:
            contexto_curricular += f"\nEstándares Básicos de Competencias (EBC) de referencia:\n{data.ebc_referencia}\n"

        instrucciones_extra = ""
        if data.instrucciones_docente:
            instrucciones_extra = f"\n\n---INSTRUCCIONES ADICIONALES DEL DOCENTE---\n{data.instrucciones_docente}"

        prompt = f"""Eres un experto en Educación Inclusiva, Diseño Universal para el Aprendizaje (DUA) y elaboración de PIAR (Plan Individual de Ajustes Razonables) según la normativa colombiana (Decreto 1421 de 2017).

Tu tarea es generar un plan de ajuste razonable COMPLETO para el área de "{data.area}" para el siguiente estudiante con necesidades de apoyo educativo:

== PERFIL DEL ESTUDIANTE ==
{contexto_estudiante}
== MALLA CURRICULAR DE REFERENCIA =={contexto_curricular if contexto_curricular else ' (No se proporcionaron DBA/EBC de referencia)'}

Genera una respuesta estructurada en EXACTAMENTE el siguiente formato (respeta las líneas separadoras):

---OBJETIVOS---
[Escribe aquí los propósitos y objetivos de aprendizaje adaptados para este estudiante en el área de {data.area}. Basa los objetivos en los DBA/EBC de referencia pero adáptalos a las capacidades del estudiante. Máximo 4 objetivos concretos.]

---BARRERAS---
[Identifica 3 a 5 barreras de aprendizaje concretas que este estudiante probablemente enfrenta en el área de {data.area}, considerando su perfil y diagnóstico. Barreras cognitivas, comunicativas, sensoriales o contextuales.]

---AJUSTES---
[Proporciona 5 a 8 estrategias DUA y ajustes razonables concretos y accionables para el docente, organizados en viñetas. Incluye adaptaciones metodológicas, de evaluación y de materiales.]{instrucciones_extra}

Responde ÚNICAMENTE con el formato especificado, sin explicaciones previas ni conclusiones posteriores."""

        # Obtener clave Gemini: BD primero, .env como fallback
        gemini_key = await get_gemini_key(db)
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Parsear la respuesta estructurada
        def extract_section(text: str, marker: str, next_marker: Optional[str]) -> str:
            start_tag = f"---{marker}---"
            start = text.find(start_tag)
            if start == -1:
                return ""
            start = start + len(start_tag)
            if next_marker:
                end_tag = f"---{next_marker}---"
                end = text.find(end_tag, start)
                return text[start:end].strip() if end != -1 else text[start:].strip()
            return text[start:].strip()

        objetivos = extract_section(raw, "OBJETIVOS", "BARRERAS")
        barreras = extract_section(raw, "BARRERAS", "AJUSTES")
        ajustes = extract_section(raw, "AJUSTES", None)

        if not objetivos or not barreras or not ajustes:
            # fallback: devolver todo si el parseo falla
            return PlanCompletoIAResponse(
                objetivos_propositos=raw,
                barreras_evidenciadas="(Ver respuesta completa en objetivos)",
                ajustes_estrategias="(Ver respuesta completa en objetivos)"
            )

        return PlanCompletoIAResponse(
            objetivos_propositos=objetivos,
            barreras_evidenciadas=barreras,
            ajustes_estrategias=ajustes
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al contactar Gemini: {str(e)}")

@router.patch("/{piar_id}", response_model=PiarResponse)
async def update_piar(
    piar_id: uuid.UUID,
    data: PiarUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza los metadatos de un PIAR (estado, docentes) y sus Características del Estudiante (gustos, habilidades)."""
    query = (
        select(PiarORM)
        .where(PiarORM.id == piar_id)
        .options(
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables),
            selectinload(PiarORM.recomendaciones_pmi)
        )
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    if data.estado is not None:
        piar.estado = data.estado
    if data.docentes_elaboran is not None:
        piar.docentes_elaboran = data.docentes_elaboran

    if data.caracteristicas is not None:
        if piar.caracteristicas:
            piar.caracteristicas.descripcion_gustos_intereses = data.caracteristicas.descripcion_gustos_intereses
            piar.caracteristicas.descripcion_habilidades = data.caracteristicas.descripcion_habilidades
        else:
            nueva_carac = CaracteristicasEstudianteORM(
                piar_id=piar.id,
                descripcion_gustos_intereses=data.caracteristicas.descripcion_gustos_intereses,
                descripcion_habilidades=data.caracteristicas.descripcion_habilidades
            )
            db.add(nueva_carac)
            piar.caracteristicas = nueva_carac

    await db.commit()
    
    # Recargar el PIAR con todas sus relaciones cargadas para la respuesta
    result = await db.execute(query)
    return result.scalars().first()

@router.put("/{piar_id}/ajustes/{ajuste_id}", response_model=AjusteRazonableResponse)
async def update_ajuste_razonable(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    data: AjusteRazonableCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Modifica un ajuste razonable existente en la matriz."""
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    ajuste.area = data.area
    ajuste.objetivos_propositos = data.objetivos_propositos
    ajuste.barreras_evidenciadas = data.barreras_evidenciadas
    ajuste.ajustes_estrategias = data.ajustes_estrategias
    ajuste.evaluacion_ajustes = data.evaluacion_ajustes

    await db.commit()
    await db.refresh(ajuste)
    return ajuste

@router.delete("/{piar_id}/ajustes/{ajuste_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ajuste_razonable(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Elimina un ajuste razonable de la matriz."""
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    await db.delete(ajuste)
    await db.commit()
    return None

@router.post("/{piar_id}/pmi", response_model=RecomendacionPMIResponse)
async def add_recomendacion_pmi(
    piar_id: uuid.UUID,
    data: RecomendacionPMICreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Crea una recomendación PMI asociada a un actor específico."""
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    nueva_rec = RecomendacionPMIORM(
        piar_id=piar_id,
        actor=data.actor,
        acciones=data.acciones,
        estrategias_implementar=data.estrategias_implementar
    )
    db.add(nueva_rec)
    await db.commit()
    await db.refresh(nueva_rec)
    return nueva_rec

@router.put("/{piar_id}/pmi/{pmi_id}", response_model=RecomendacionPMIResponse)
async def update_recomendacion_pmi(
    piar_id: uuid.UUID,
    pmi_id: uuid.UUID,
    data: RecomendacionPMICreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Modifica una recomendación PMI existente."""
    rec = await db.get(RecomendacionPMIORM, pmi_id)
    if not rec or rec.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Recomendación PMI no encontrada en este PIAR.")

    rec.actor = data.actor
    rec.acciones = data.acciones
    rec.estrategias_implementar = data.estrategias_implementar

    await db.commit()
    await db.refresh(rec)
    return rec

@router.delete("/{piar_id}/pmi/{pmi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recomendacion_pmi(
    piar_id: uuid.UUID,
    pmi_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Elimina una recomendación PMI."""
    rec = await db.get(RecomendacionPMIORM, pmi_id)
    if not rec or rec.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Recomendación PMI no encontrada en este PIAR.")

    await db.delete(rec)
    await db.commit()
    return None

