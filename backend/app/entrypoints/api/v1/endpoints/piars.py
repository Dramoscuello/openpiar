import uuid
import json
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import google.generativeai as genai          # SDK legacy — usado solo en /generar_ia
from google import genai as genai_new        # SDK nuevo — usado en /generar_plan_ia
from google.genai import types as genai_types

from app.core.config import get_settings
from app.adapters.db.session import get_db
from app.adapters.db.models import (
    PiarORM,
    CaracteristicasEstudianteORM,
    AjusteRazonableORM,
    EvidenciaAjusteORM,
    PeriodoAcademicoORM,
    EstudianteORM,
    RecomendacionPMIORM,
    ConfiguracionSistemaORM,
    ActaAcuerdoORM,
    CompromisoCasaORM,
    AuditoriaCambioORM,
    GrupoORM,
    GradoORM,
    EntornoSaludORM,
    EntornoHogarORM,
    TrayectoriaEducativaORM,
    MatriculaActualORM,
    AsignaturaORM,
    CargaAcademicaORM,
    UsuarioORM,
)
from app.entrypoints.api.schemas import (
    PiarCreate,
    PiarUpdate,
    PiarResponse,
    AjusteRazonableCreate,
    AjusteRazonableResponse,
    AjustePuntuacionRequest,
    GenerarAjustesRequest,
    GenerarPlanCompletoRequest,
    PlanCompletoIAResponse,
    BaseResponse,
    RecomendacionPMICreate,
    RecomendacionPMIResponse,
    ActaAcuerdoCreate,
    ActaAcuerdoResponse,
    AuditoriaCambioResponse,
    AuditoriaListResponse,
    EvidenciaAjusteCreate,
    EvidenciaAjusteResponse,
    AjusteRazonableConEvidenciasResponse,
)
from app.entrypoints.api.dependencies import CurrentUser

from app.entrypoints.api.v1.endpoints.auditoria_helpers import (
    registrar_cambio,
    serializar_ajuste,
    serializar_pmi,
    serializar_acta,
    serializar_caracteristicas,
    serializar_estado_piar,
    serializar_evidencia,
)

router = APIRouter(prefix="/piars", tags=["piars"])
settings = get_settings()


def _build_ajustes_response(ajustes_orm: list) -> list:
    items = []
    for a in ajustes_orm:
        evidence_list = []
        for ev in (a.evidencias or []):
            evidence_list.append(EvidenciaAjusteResponse(
                id=ev.id,
                ajuste_razonable_id=ev.ajuste_razonable_id,
                piar_id=ev.piar_id,
                nombre_archivo=ev.nombre_archivo,
                tipo_archivo=ev.tipo_archivo,
                descripcion=ev.descripcion,
                fecha=ev.fecha,
                creado_por=ev.creado_por,
                creador_nombre=f"{ev.creador.nombre} {ev.creador.apellido}" if ev.creador else None,
                fecha_subida=ev.fecha_subida,
            ))
        items.append(AjusteRazonableConEvidenciasResponse(
            id=a.id,
            piar_id=a.piar_id,
            periodo_id=a.periodo_id,
            creado_por=a.creado_por,
            area=a.area,
            titulo_tema=a.titulo_tema,
            objetivos_propositos=a.objetivos_propositos,
            barreras_evidenciadas=a.barreras_evidenciadas,
            ajustes_estrategias=a.ajustes_estrategias,
            evaluacion_ajustes=a.evaluacion_ajustes,
            puntuacion=a.puntuacion,
            comentario_puntuacion=a.comentario_puntuacion,
            evidencias=evidence_list,
        ))
    return items


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
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias),
            selectinload(PiarORM.recomendaciones_pmi),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa)
        )
        .order_by(PiarORM.created_at.desc())
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado para este estudiante.")

    es_directivo = current_user.rol.es_directivo
    es_director = False
    if not es_directivo:
        estudiante = await db.get(EstudianteORM, estudiante_id)
        if estudiante and estudiante.grupo_id:
            grupo = await db.get(GrupoORM, estudiante.grupo_id)
            if grupo and grupo.director_id == current_user.id:
                es_director = True

    director_nombre = None
    if piar.estudiante and piar.estudiante.grupo and piar.estudiante.grupo.director:
        d = piar.estudiante.grupo.director
        director_nombre = f"{d.nombre} {d.apellido}"

    response = PiarResponse.model_validate(piar)

    response.ajustes_razonables = _build_ajustes_response(piar.ajustes_razonables)
    response.director_nombre = director_nombre

    if not es_directivo and not es_director:
        response.ajustes_razonables = [
            a for a in response.ajustes_razonables
            if a.creado_por == current_user.id
        ]
    return response

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

    if not estudiante.codigo_acceso_familia:
        import secrets
        estudiante.codigo_acceso_familia = secrets.token_hex(4)[:8]
        await db.commit()

    await registrar_cambio(
        db=db,
        entidad_tipo="piar_estado",
        entidad_id=nuevo_piar.id,
        piar_id=nuevo_piar.id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos={"estado": nuevo_piar.estado},
    )

    # Consultar el PIAR recién creado cargando todas sus relaciones para la respuesta
    query = (
        select(PiarORM)
        .where(PiarORM.id == nuevo_piar.id)
        .options(
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias),
            selectinload(PiarORM.recomendaciones_pmi),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa)
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
        creado_por=current_user.id,
        area=data.area,
        titulo_tema=data.titulo_tema,
        objetivos_propositos=data.objetivos_propositos,
        barreras_evidenciadas=data.barreras_evidenciadas,
        ajustes_estrategias=data.ajustes_estrategias,
        evaluacion_ajustes=data.evaluacion_ajustes
    )
    db.add(nuevo_ajuste)
    await db.commit()
    await db.refresh(nuevo_ajuste)

    await registrar_cambio(
        db=db,
        entidad_tipo="ajuste_razonable",
        entidad_id=nuevo_ajuste.id,
        piar_id=piar_id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos=serializar_ajuste(nuevo_ajuste),
    )

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
        )
        if data.titulo_tema:
            prompt += f"- Título del Tema: {data.titulo_tema}\n"
        prompt += (
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
    """
    Genera ajustes razonables DUA usando Gemini (nuevo SDK google-genai).
    Los objetivos y las barreras los define el docente; la IA se enfoca en sugerir los ajustes razonables.
    Usa JSON structured output para garantizar texto limpio sin markdown.
    """
    try:
        # Verificar PIAR
        piar = await db.get(PiarORM, piar_id)
        if not piar:
            raise HTTPException(status_code=404, detail="PIAR no encontrado.")

        # --- Obtener contexto institucional para la IA ---
        result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
        config = result.scalars().first()
        contexto_institucion = config.contexto_institucion if config else None

        # --- Construir bloque de perfil del estudiante ---
        perfil_parts = [f"Nombre: {data.estudiante_nombre}"]
        if data.edad is not None:
            perfil_parts.append(f"Edad: {data.edad} años")
        if data.grado:
            perfil_parts.append(f"Grado escolar: {data.grado}")
        if data.diagnostico_medico:
            perfil_parts.append(f"Diagnóstico o condición reportada: {data.diagnostico_medico}")
        if data.gustos_intereses:
            perfil_parts.append(f"Gustos, intereses y expectativas familiares: {data.gustos_intereses}")
        if data.habilidades_fortalezas:
            perfil_parts.append(f"Habilidades, fortalezas y apoyos actuales: {data.habilidades_fortalezas}")
        perfil_texto = "\n".join(perfil_parts)

        # --- Construir bloque curricular de referencia ---
        curricular_parts = []
        if data.dba_referencia:
            curricular_parts.append(
                f"Derechos Básicos de Aprendizaje (DBA) para el grado {data.grado or ''}:\n{data.dba_referencia}"
            )
        if data.ebc_referencia:
            curricular_parts.append(
                f"Estándares Básicos de Competencias (EBC):\n{data.ebc_referencia}"
            )
        curricular_texto = ("\n\n".join(curricular_parts)
                            if curricular_parts else "No se proporcionaron DBA/EBC de referencia.")

        instrucciones_extra = (
            f"\n\nNota adicional del docente: {data.instrucciones_docente}"
            if data.instrucciones_docente else ""
        )

        # --- Prompt optimizado con chain-of-thought y contexto de dominio ---
        # Basado en: Decreto 1421/2017, Decreto 1860/1994, Ley 2216/2022 y DUA
        prompt = f"""Eres un especialista en Educación Inclusiva colombiana con profundo conocimiento del Decreto 1421 de 2017, Decreto 1860 de 1994, Ley 2216 de 2022 y el Diseño Universal para el Aprendizaje (DUA). Tu función es asistir a docentes en la elaboración del PIAR (Plan Individual de Ajustes Razonables).

El docente ya definió los objetivos de aprendizaje y las barreras identificadas. Tu tarea consiste EXCLUSIVAMENTE en proponer los ajustes razonables concretos, pedagógicos y accionables que minimicen esas barreras.

AREA O ASIGNATURA: {data.area}
TÍTULO DEL TEMA O TEMÁTICA: {data.titulo_tema if data.titulo_tema else 'No especificado'}

PERFIL DEL ESTUDIANTE:
{perfil_texto}

BARRERAS IDENTIFICADAS POR EL DOCENTE EN ESTE CONTEXTO:
{data.barreras_evidenciadas}

REFERENCIA CURRICULAR (para contexto de los ajustes):
{curricular_texto}{instrucciones_extra}
{("""
CONTEXTO INSTITUCIONAL:
""" + contexto_institucion + """

IMPORTANTE SOBRE EL CONTEXTO INSTITUCIONAL: Los ajustes razonables que propongas deben ser realistas y viables dentro del contexto real de esta institución. No sugieras recursos tecnológicos, infraestructura, personal especializado o apoyos externos que no estén disponibles en este entorno específico. Por ejemplo: si la institución es rural y tiene conectividad limitada, no propongas estrategias que dependan de internet de alta velocidad, laboratorios especializados o equipos sofisticados. Adapta tus sugerencias a los recursos y posibilidades reales del entorno escolar descrito.
""") if contexto_institucion else ""}

MARCO NORMATIVO A CONSIDERAR PARA LOS AJUSTES:
- Decreto 1421 de 2017 (Inclusión y Ajustes Razonables): Proponer adaptaciones eficaces basadas en las necesidades específicas del estudiante, promoviendo la máxima autonomía y permanencia dentro del aula regular junto a sus pares, sin segregación.
- Decreto 1860 de 1994 (Flexibilidad): Asegurar la flexibilización de metodologías, ritmos de aprendizaje y formas de evaluación, adaptándose a la diversidad y edad cronológica del educando.
- Ley 2216 de 2022 (Dificultades/Trastornos de Aprendizaje): En caso de dificultades de lectura, escritura, cálculos o procesamiento de información, incorporar estrategias didácticas específicas, recursos metodológicos y herramientas tecnológicas sin aislar al estudiante del aula regular, articulando pautas para la continuidad del acompañamiento en casa por parte de la familia.
- Edad del estudiante: Los apoyos sugeridos deben ser pedagógicamente adecuados para un estudiante de su edad ({data.edad if data.edad else 'no especificada'} años).

CATEGORÍAS DE APOYO A CONSIDERAR (según el catálogo colombiano de ajustes):
- Mediaciones discursivas: comunicación, ritmos de instrucción, alternativas de lenguaje.
- Situación de aprendizaje: didáctica flexible, tareas secuenciadas, multisensorialidad, agrupamientos.
- Productos y tecnología: herramientas de apoyo, organizadores visuales, uso de TICs, materiales adaptados.
- Personas: redes de compañeros, mediadores, docentes de apoyo, vinculación de la familia.
- Entorno físico: ubicación del estudiante, adecuación de espacios, manejo de estímulos o distractores.
- Servicio y comunidad: articulación con recomendaciones terapéuticas del sector salud.
- Entorno socioeducativo: clima inclusivo, regulación socioemocional, fomento de la autoestima y participación.

Reglas de formato para tu respuesta JSON:
- Proporciona un texto consolidado en español, organizado en oraciones completas y directas, separadas con punto y aparte.
- No uses listas con viñetas, guiones ni asteriscos.
- No uses negritas, cursivas, títulos ni ningún formato markdown (sin '#' ni '*').
- Sé altamente específico y accionable: el docente de aula debe poder aplicar cada ajuste directamente en su planeación.
- Escribe en tercera persona o imperativo (ej: "Presentar la información...", "El estudiante requiere...")."""

        # --- Esquema JSON para structured output ---
        schema_json = {
            "type": "object",
            "properties": {
                "ajustes_estrategias": {
                    "type": "string",
                    "description": "Ajustes razonables y estrategias DUA propuestos. Texto plano, consolidado, sin listas ni markdown. Cada ajuste separado con punto y aparte."
                }
            },
            "required": ["ajustes_estrategias"]
        }

        # --- Llamar a Gemini con el nuevo SDK (google-genai) ---
        gemini_key = await get_gemini_key(db)
        client = genai_new.Client(api_key=gemini_key)

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema_json,
                temperature=0.4,
            )
        )

        # El SDK nuevo garantiza JSON válido cuando se usa response_mime_type
        parsed = json.loads(response.text)

        return PlanCompletoIAResponse(
            ajustes_estrategias=parsed.get("ajustes_estrategias", "").strip()
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
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias),
            selectinload(PiarORM.recomendaciones_pmi),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa)
        )
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    # Rechazar solo cambio de estado si ya está firmado (contenido siempre editable)
    if piar.estado == "firmado" and data.estado is not None and data.estado != "firmado":
        raise HTTPException(
            status_code=409,
            detail="No se puede cambiar el estado de un PIAR ya firmado."
        )

    estado_anterior = piar.estado
    carac_anteriores = serializar_caracteristicas(piar.caracteristicas) if piar.caracteristicas else None

    if data.estado == "firmado":
        if not piar.acta_acuerdo:
            raise HTTPException(
                status_code=409,
                detail="Debe existir un acta de acuerdo guardada antes de finalizar el PIAR."
            )
        acta = piar.acta_acuerdo
        firmas_faltantes = []
        if not acta.firmado_estudiante:
            firmas_faltantes.append("Estudiante")
        if not acta.firmado_acudiente:
            firmas_faltantes.append("Acudiente / Familia")
        if not acta.firmado_docentes_aula:
            firmas_faltantes.append("Docentes de Aula")
        if not acta.firmado_directivo:
            firmas_faltantes.append("Directivo docente (Rector)")
        if firmas_faltantes:
            raise HTTPException(
                status_code=409,
                detail=f"Faltan las firmas de: {', '.join(firmas_faltantes)}. "
                       f"Todas las partes deben firmar antes de finalizar el PIAR."
            )
        piar.estado = "firmado"
    elif data.estado is not None:
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

    if data.estado is not None and data.estado != estado_anterior:
        await registrar_cambio(
            db=db,
            entidad_tipo="piar_estado",
            entidad_id=piar.id,
            piar_id=piar.id,
            accion="modificar",
            usuario_id=current_user.id,
            datos_anteriores=serializar_estado_piar(estado_anterior),
            datos_nuevos=serializar_estado_piar(data.estado),
        )

    if data.caracteristicas is not None and piar.caracteristicas:
        await registrar_cambio(
            db=db,
            entidad_tipo="caracteristicas_estudiante",
            entidad_id=piar.caracteristicas.id,
            piar_id=piar.id,
            accion="crear" if carac_anteriores is None else "modificar",
            usuario_id=current_user.id,
            datos_anteriores=carac_anteriores,
            datos_nuevos=serializar_caracteristicas(piar.caracteristicas),
        )

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

    if ajuste.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente que creó el ajuste puede adjuntar evidencias.")

    datos_antes = serializar_ajuste(ajuste)

    ajuste.area = data.area
    ajuste.titulo_tema = data.titulo_tema
    ajuste.objetivos_propositos = data.objetivos_propositos
    ajuste.barreras_evidenciadas = data.barreras_evidenciadas
    ajuste.ajustes_estrategias = data.ajustes_estrategias
    ajuste.evaluacion_ajustes = data.evaluacion_ajustes

    await db.commit()
    await db.refresh(ajuste)

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

    return ajuste


@router.patch("/{piar_id}/ajustes/{ajuste_id}/puntuacion", response_model=AjusteRazonableResponse)
async def puntuar_ajuste(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    data: AjustePuntuacionRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Puntúa un ajuste razonable (1-5) con comentario. Solo el creador puede hacerlo."""
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    if ajuste.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente que creó el ajuste puede adjuntar evidencias.")

    if ajuste.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente que creó el ajuste puede puntuarlo.")

    datos_antes = serializar_ajuste(ajuste)
    ajuste.puntuacion = data.puntuacion
    ajuste.comentario_puntuacion = data.comentario

    await db.commit()
    await db.refresh(ajuste)

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

    if ajuste.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente que creó el ajuste puede adjuntar evidencias.")

    datos_antes = serializar_ajuste(ajuste)
    ajuste_id = ajuste.id

    await db.delete(ajuste)
    await db.commit()

    await registrar_cambio(
        db=db,
        entidad_tipo="ajuste_razonable",
        entidad_id=ajuste_id,
        piar_id=piar_id,
        accion="eliminar",
        usuario_id=current_user.id,
        datos_anteriores=datos_antes,
    )

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

    await registrar_cambio(
        db=db,
        entidad_tipo="recomendacion_pmi",
        entidad_id=nueva_rec.id,
        piar_id=piar_id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos=serializar_pmi(nueva_rec),
    )

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

    datos_antes = serializar_pmi(rec)
    rec.actor = data.actor
    rec.acciones = data.acciones
    rec.estrategias_implementar = data.estrategias_implementar

    await db.commit()
    await db.refresh(rec)

    await registrar_cambio(
        db=db,
        entidad_tipo="recomendacion_pmi",
        entidad_id=rec.id,
        piar_id=piar_id,
        accion="modificar",
        usuario_id=current_user.id,
        datos_anteriores=datos_antes,
        datos_nuevos=serializar_pmi(rec),
    )

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

    datos_antes = serializar_pmi(rec)
    pmi_id = rec.id

    await db.delete(rec)
    await db.commit()

    await registrar_cambio(
        db=db,
        entidad_tipo="recomendacion_pmi",
        entidad_id=pmi_id,
        piar_id=piar_id,
        accion="eliminar",
        usuario_id=current_user.id,
        datos_anteriores=datos_antes,
    )

    return None


@router.get("/{piar_id}/acta", response_model=Optional[ActaAcuerdoResponse])
async def get_acta_acuerdo(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el Acta de Acuerdo (Anexo 3) para un PIAR, si existe."""
    query = (
        select(ActaAcuerdoORM)
        .where(ActaAcuerdoORM.piar_id == piar_id)
        .options(selectinload(ActaAcuerdoORM.compromisos_casa))
    )
    result = await db.execute(query)
    acta = result.scalars().first()
    return acta


@router.post("/{piar_id}/acta", response_model=ActaAcuerdoResponse)
async def upsert_acta_acuerdo(
    piar_id: uuid.UUID,
    data: ActaAcuerdoCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Crea o actualiza el Acta de Acuerdo (Anexo 3) para un PIAR, y sincroniza las actividades de casa."""
    # Verificar si el PIAR existe
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    # Buscar si ya existe acta para este PIAR
    query = (
        select(ActaAcuerdoORM)
        .where(ActaAcuerdoORM.piar_id == piar_id)
        .options(selectinload(ActaAcuerdoORM.compromisos_casa))
    )
    result = await db.execute(query)
    acta = result.scalars().first()

    if not acta:
        # Crear nueva acta
        acta = ActaAcuerdoORM(
            piar_id=piar_id,
            fecha_firma=data.fecha_firma,
            compromisos_aula=data.compromisos_aula,
            firmado_estudiante=data.firmado_estudiante,
            firmado_acudiente=data.firmado_acudiente,
            firmado_docente_apoyo=data.firmado_docente_apoyo,
            firmado_docentes_aula=data.firmado_docentes_aula,
            firmado_directivo=data.firmado_directivo,
            compromisos_casa=[]
        )
        db.add(acta)
        await db.flush()
        es_creacion = True
        datos_acta_antes = None
    else:
        es_creacion = False
        datos_acta_antes = serializar_acta(acta)
        acta.fecha_firma = data.fecha_firma
        acta.compromisos_aula = data.compromisos_aula
        acta.firmado_estudiante = data.firmado_estudiante
        acta.firmado_acudiente = data.firmado_acudiente
        acta.firmado_docente_apoyo = data.firmado_docente_apoyo
        acta.firmado_docentes_aula = data.firmado_docentes_aula
        acta.firmado_directivo = data.firmado_directivo

    # Sincronizar compromisos de casa (borrar antiguos, crear nuevos)
    for comp in list(acta.compromisos_casa):
        await db.delete(comp)
    
    for comp_in in data.compromisos_casa:
        nuevo_comp = CompromisoCasaORM(
            acta_id=acta.id,
            nombre_actividad=comp_in.nombre_actividad,
            descripcion_estrategia=comp_in.descripcion_estrategia,
            frecuencia=comp_in.frecuencia
        )
        db.add(nuevo_comp)

    await db.commit()

    await registrar_cambio(
        db=db,
        entidad_tipo="acta_acuerdo",
        entidad_id=acta.id,
        piar_id=piar_id,
        accion="crear" if es_creacion else "modificar",
        usuario_id=current_user.id,
        datos_anteriores=datos_acta_antes,
        datos_nuevos=serializar_acta(acta),
    )

    from app.core.notification_service import notificar_firma_pendiente_evento
    await notificar_firma_pendiente_evento(db, piar.id, piar.estudiante_id)

    # Recargar para devolver la respuesta con los compromisos de casa cargados
    query = (
        select(ActaAcuerdoORM)
        .where(ActaAcuerdoORM.id == acta.id)
        .options(selectinload(ActaAcuerdoORM.compromisos_casa))
    )
    res = await db.execute(query)
    return res.scalars().first()


@router.get("/{piar_id}/acta/pdf")
async def download_acta_pdf(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Genera y descarga el PDF oficial del Acta de Acuerdo (Anexo 3) para un PIAR."""
    # Buscar el PIAR con relaciones cargadas
    query = (
        select(PiarORM)
        .where(PiarORM.id == piar_id)
        .options(
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.grado),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.sede),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.asignatura),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_salud),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_hogar),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.trayectoria_educativa),
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.matricula_actual),
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.periodo),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias).selectinload(EvidenciaAjusteORM.creador),
            selectinload(PiarORM.recomendaciones_pmi),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa)
        )
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    
    if not piar.acta_acuerdo:
        raise HTTPException(
            status_code=400,
            detail="Debe completar y guardar el Acta de Acuerdo (Anexo 3) antes de generar el PDF."
        )

    # Cargar todos los periodos académicos y determinar los activos/pasados
    from datetime import date
    periodos_result = await db.execute(
        select(PeriodoAcademicoORM).order_by(PeriodoAcademicoORM.fecha_inicio)
    )
    all_periodos = periodos_result.scalars().all()

    # Identificar periodos con ajustes para este estudiante
    periods_with_adjustments = {aj.periodo_id for aj in piar.ajustes_razonables if aj.periodo_id}

    # Filtrar periodos que están/estuvieron activos o tienen información
    selected_periods = []
    today = date.today()
    for p in all_periodos:
        if p.activo or p.fecha_inicio <= today or p.id in periods_with_adjustments:
            selected_periods.append(p)

    # Cargar la configuración del sistema
    config_result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = config_result.scalars().first()

    # Generar el PDF
    from app.core.pdf_generator import generate_acta_pdf
    pdf_bytes = generate_acta_pdf(piar, config, selected_periods)

    # Retornar como archivo descargable
    filename = f"Acta_Acuerdo_{piar.estudiante.numero_documento}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ---------------------------------------------------------------------------
# Portafolio de Evidencias del Estudiante
# ---------------------------------------------------------------------------

UPLOAD_DIR = "uploads/evidencias"

@router.post(
    "/{piar_id}/ajustes/{ajuste_id}/evidencias",
    response_model=EvidenciaAjusteResponse,
)
async def upload_evidencia(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    descripcion: str = Form(..., min_length=2),
    fecha: date = Form(...),
):
    """Sube una imagen o PDF como evidencia de un ajuste DUA (máx 15 MB)."""
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    if ajuste.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente que creó el ajuste puede adjuntar evidencias.")

    filename = (file.filename or "evidencia").lower()
    if filename.endswith((".jpg", ".jpeg", ".png")):
        tipo = "imagen"
    elif filename.endswith(".pdf"):
        tipo = "pdf"
    else:
        raise HTTPException(
            status_code=422,
            detail="Solo se permiten imágenes (JPG, PNG) o documentos PDF.",
        )

    contenido = await file.read()
    if len(contenido) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 15 MB.")

    import os as _os
    upload_dir = _os.path.join(UPLOAD_DIR, str(piar_id))
    _os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    ext = _os.path.splitext(filename)[1]
    stored_name = f"{file_id}{ext}"
    file_path = _os.path.join(upload_dir, stored_name)

    with open(file_path, "wb") as f:
        f.write(contenido)

    evidencia = EvidenciaAjusteORM(
        ajuste_razonable_id=ajuste_id,
        piar_id=piar_id,
        nombre_archivo=filename,
        tipo_archivo=tipo,
        ruta_archivo=file_path,
        descripcion=descripcion,
        fecha=fecha,
        creado_por=current_user.id,
    )
    db.add(evidencia)
    await db.commit()
    await db.refresh(evidencia)

    await registrar_cambio(
        db=db,
        entidad_tipo="evidencia_ajuste",
        entidad_id=evidencia.id,
        piar_id=piar_id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos=serializar_evidencia(
            evidencia.nombre_archivo, evidencia.descripcion, evidencia.fecha
        ),
    )

    return EvidenciaAjusteResponse(
        id=evidencia.id,
        ajuste_razonable_id=evidencia.ajuste_razonable_id,
        piar_id=evidencia.piar_id,
        nombre_archivo=evidencia.nombre_archivo,
        tipo_archivo=evidencia.tipo_archivo,
        descripcion=evidencia.descripcion,
        fecha=evidencia.fecha,
        creado_por=evidencia.creado_por,
        fecha_subida=evidencia.fecha_subida,
    )


@router.get(
    "/{piar_id}/ajustes/{ajuste_id}/evidencias",
)
async def list_evidencias_ajuste(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lista las evidencias de un ajuste DUA."""
    query = (
        select(EvidenciaAjusteORM)
        .where(
            EvidenciaAjusteORM.piar_id == piar_id,
            EvidenciaAjusteORM.ajuste_razonable_id == ajuste_id,
        )
        .options(selectinload(EvidenciaAjusteORM.creador))
        .order_by(EvidenciaAjusteORM.fecha.desc())
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        EvidenciaAjusteResponse(
            id=e.id,
            ajuste_razonable_id=e.ajuste_razonable_id,
            piar_id=e.piar_id,
            nombre_archivo=e.nombre_archivo,
            tipo_archivo=e.tipo_archivo,
            descripcion=e.descripcion,
            fecha=e.fecha,
            creado_por=e.creado_por,
            creador_nombre=f"{e.creador.nombre} {e.creador.apellido}" if e.creador else None,
            fecha_subida=e.fecha_subida,
        )
        for e in items
    ]


@router.get(
    "/{piar_id}/evidencias",
)
async def list_evidencias_piar(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lista todas las evidencias del PIAR (para timeline y PDF)."""
    query = (
        select(EvidenciaAjusteORM)
        .where(EvidenciaAjusteORM.piar_id == piar_id)
        .options(selectinload(EvidenciaAjusteORM.creador))
        .order_by(EvidenciaAjusteORM.fecha.desc())
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        EvidenciaAjusteResponse(
            id=e.id,
            ajuste_razonable_id=e.ajuste_razonable_id,
            piar_id=e.piar_id,
            nombre_archivo=e.nombre_archivo,
            tipo_archivo=e.tipo_archivo,
            descripcion=e.descripcion,
            fecha=e.fecha,
            creado_por=e.creado_por,
            creador_nombre=f"{e.creador.nombre} {e.creador.apellido}" if e.creador else None,
            fecha_subida=e.fecha_subida,
        )
        for e in items
    ]


@router.get(
    "/{piar_id}/evidencias/{evidencia_id}/descargar",
)
async def descargar_evidencia(
    piar_id: uuid.UUID,
    evidencia_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Descarga el archivo de una evidencia."""
    evidencia = await db.get(EvidenciaAjusteORM, evidencia_id)
    if not evidencia or evidencia.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")

    import os as _os
    if not _os.path.exists(evidencia.ruta_archivo):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor.")

    media_type = "image/png" if evidencia.tipo_archivo == "imagen" else "application/pdf"
    with open(evidencia.ruta_archivo, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{evidencia.nombre_archivo}"'
        },
    )


@router.delete(
    "/{piar_id}/evidencias/{evidencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_evidencia(
    piar_id: uuid.UUID,
    evidencia_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Elimina una evidencia y su archivo."""
    evidencia = await db.get(EvidenciaAjusteORM, evidencia_id)
    if not evidencia or evidencia.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")

    if evidencia.creado_por != current_user.id:
        raise HTTPException(status_code=403, detail="Solo quien subió la evidencia puede eliminarla.")

    nombre = evidencia.nombre_archivo
    desc = evidencia.descripcion
    fecha = evidencia.fecha

    import os as _os
    if _os.path.exists(evidencia.ruta_archivo):
        _os.remove(evidencia.ruta_archivo)

    ev_id = evidencia.id
    await db.delete(evidencia)
    await db.commit()

    await registrar_cambio(
        db=db,
        entidad_tipo="evidencia_ajuste",
        entidad_id=ev_id,
        piar_id=piar_id,
        accion="eliminar",
        usuario_id=current_user.id,
        datos_anteriores=serializar_evidencia(nombre, desc, fecha),
    )

    return None


# ---------------------------------------------------------------------------
# Auditoría — Historial de cambios del PIAR
# ---------------------------------------------------------------------------

@router.get(
    "/{piar_id}/historial",
    response_model=AuditoriaListResponse,
)
async def get_historial_piar(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Obtiene el historial completo de cambios de un PIAR."""
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    query = (
        select(AuditoriaCambioORM)
        .where(AuditoriaCambioORM.piar_id == piar_id)
        .options(selectinload(AuditoriaCambioORM.usuario))
        .order_by(AuditoriaCambioORM.fecha.desc())
    )
    count_query = (
        select(AuditoriaCambioORM)
        .where(AuditoriaCambioORM.piar_id == piar_id)
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    items = []
    for r in rows:
        items.append(AuditoriaCambioResponse(
            id=r.id,
            entidad_tipo=r.entidad_tipo,
            entidad_id=r.entidad_id,
            piar_id=r.piar_id,
            accion=r.accion,
            usuario_id=r.usuario_id,
            usuario_nombre=f"{r.usuario.nombre} {r.usuario.apellido}" if r.usuario else None,
            datos_anteriores=r.datos_anteriores,
            datos_nuevos=r.datos_nuevos,
            fecha=r.fecha,
            ip_origen=r.ip_origen,
        ))

    return AuditoriaListResponse(total=total, items=items)


@router.get(
    "/{piar_id}/historial/diff",
)
async def diff_versiones(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    v1: Optional[uuid.UUID] = None,
    v2: Optional[uuid.UUID] = None,
):
    """Compara dos versiones de una entidad auditada (diff)."""
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    if not v1 or not v2:
        raise HTTPException(
            status_code=400,
            detail="Debe especificar los IDs de ambas versiones: ?v1=uuid&v2=uuid"
        )

    query = (
        select(AuditoriaCambioORM)
        .where(
            AuditoriaCambioORM.id.in_([v1, v2]),
            AuditoriaCambioORM.piar_id == piar_id,
        )
        .order_by(AuditoriaCambioORM.fecha)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    if len(rows) != 2:
        raise HTTPException(status_code=404, detail="Una o ambas versiones no encontradas.")

    return {
        "version_anterior": {
            "id": rows[0].id,
            "fecha": rows[0].fecha.isoformat(),
            "accion": rows[0].accion,
            "datos": rows[0].datos_nuevos or rows[0].datos_anteriores,
        },
        "version_posterior": {
            "id": rows[1].id,
            "fecha": rows[1].fecha.isoformat(),
            "accion": rows[1].accion,
            "datos": rows[1].datos_nuevos or rows[1].datos_anteriores,
        },
    }


@router.get(
    "/{piar_id}/historial/exportar-pdf",
)
async def export_historial_pdf(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Genera y descarga un PDF con la trazabilidad completa del PIAR."""
    piar = await db.get(PiarORM, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    query = (
        select(AuditoriaCambioORM)
        .where(AuditoriaCambioORM.piar_id == piar_id)
        .options(selectinload(AuditoriaCambioORM.usuario))
        .order_by(AuditoriaCambioORM.fecha.desc())
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    config_result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = config_result.scalars().first()

    estudiante_result = await db.execute(
        select(EstudianteORM).join(PiarORM).where(PiarORM.id == piar_id)
    )
    estudiante_orm = estudiante_result.scalars().first()

    if estudiante_orm and estudiante_orm.grupo_id:
        grupo_result = await db.execute(
            select(GrupoORM).where(GrupoORM.id == estudiante_orm.grupo_id)
        )
        estudiante_orm.grupo = grupo_result.scalars().first()

    if estudiante_orm and estudiante_orm.grupo and estudiante_orm.grupo.grado_id:
        grado_result = await db.execute(
            select(GradoORM).where(GradoORM.id == estudiante_orm.grupo.grado_id)
        )
        estudiante_orm.grupo.grado = grado_result.scalars().first()

    from app.core.pdf_generator import generate_auditoria_pdf
    pdf_bytes = generate_auditoria_pdf(piar_id, rows, config, estudiante_orm)

    doc = estudiante_orm.numero_documento if estudiante_orm else str(piar_id)[:8]
    filename = f"Auditoria_PIAR_{doc}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

