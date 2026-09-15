# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import uuid
import json
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Response, Query
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
    PiarParticipanteORM,
    PiarAsignaturaORM,
    PiarVersionORM,
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
    ActaAcuerdoCreate,
    ActaAcuerdoResponse,
    AuditoriaCambioResponse,
    AuditoriaListResponse,
    EvidenciaAjusteCreate,
    EvidenciaAjusteResponse,
    AjusteRazonableConEvidenciasResponse,
    PiarAsignaturaEstadoUpdate,
    PiarAsignaturaResponse,
    PiarCompletitudResponse,
    PiarSeccionCompletitud,
    PiarVersionResponse,
)
from app.entrypoints.api.dependencies import CurrentUser

from app.entrypoints.api.v1.endpoints.auditoria_helpers import (
    registrar_cambio,
    serializar_ajuste,
    serializar_acta,
    serializar_caracteristicas,
    serializar_estado_piar,
    serializar_evidencia,
)
from app.use_cases.piars import (
    EvaluarCompletitudPiarUseCase,
    FinalizarPiarUseCase,
    PiarCompletitudData,
    PiarIncompletoError,
    ReabrirPiarUseCase,
    VersionarPiarUseCase,
)

router = APIRouter(prefix="/piars", tags=["piars"])
settings = get_settings()


def _opciones_piar_completo() -> tuple:
    """Relaciones necesarias para completitud, PDF y versionado."""
    return (
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.grado),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.sede),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.asignatura).selectinload(AsignaturaORM.area),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.docente),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_salud),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.entorno_hogar),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.trayectoria_educativa),
        selectinload(PiarORM.estudiante).selectinload(EstudianteORM.matricula_actual),
        selectinload(PiarORM.caracteristicas),
        selectinload(PiarORM.participantes),
        selectinload(PiarORM.asignaturas_estado),
        selectinload(PiarORM.versiones),
        selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.periodo),
        selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.creador),
        selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias).selectinload(EvidenciaAjusteORM.creador),
        selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa),
    )


async def _cargar_piar_completo(db: AsyncSession, piar_id: uuid.UUID) -> Optional[PiarORM]:
    resultado = await db.execute(
        select(PiarORM).where(PiarORM.id == piar_id).options(*_opciones_piar_completo())
    )
    return resultado.scalars().first()


async def _exigir_director_o_directivo(
    piar: PiarORM, current_user, db: AsyncSession
) -> None:
    if current_user.rol.es_directivo:
        return
    grupo = piar.estudiante.grupo if piar.estudiante else None
    if grupo and grupo.director_id == current_user.id:
        return
    raise HTTPException(
        status_code=403,
        detail="Solo el director de grupo o un directivo puede realizar esta acción.",
    )


def _exigir_piar_editable(piar: PiarORM) -> None:
    if piar.estado == "firmado":
        raise HTTPException(
            status_code=409,
            detail="El PIAR está finalizado. Debe reabrirse para crear una nueva versión.",
        )


def _buscar_cobertura_asignatura(
    piar: PiarORM, asignatura_id: Optional[uuid.UUID], area: str
) -> Optional[PiarAsignaturaORM]:
    if asignatura_id:
        return next(
            (item for item in piar.asignaturas_estado if item.asignatura_id == asignatura_id),
            None,
        )
    coincidencias = [
        item for item in piar.asignaturas_estado
        if item.nombre_asignatura.strip().casefold() == area.strip().casefold()
    ]
    return coincidencias[0] if len(coincidencias) == 1 else None


def _exigir_permiso_asignatura(cobertura: PiarAsignaturaORM, current_user) -> None:
    if cobertura.docente_id and cobertura.docente_id == current_user.id:
        return
    raise HTTPException(
        status_code=403,
        detail="Solo el docente asignado a esta asignatura puede modificar sus ajustes o su justificación de cobertura.",
    )


def _ajustes_visibles_para_usuario(piar: PiarORM, current_user) -> list:
    """La dirección consulta la malla completa; cada docente, su propia autoría y asignación."""
    grupo = piar.estudiante.grupo if piar.estudiante else None
    if current_user.rol.es_directivo or (grupo and grupo.director_id == current_user.id):
        return list(piar.ajustes_razonables)
    visibles = []
    for ajuste in piar.ajustes_razonables:
        cobertura = _buscar_cobertura_asignatura(piar, ajuste.asignatura_id, ajuste.area)
        if (ajuste.creado_por == current_user.id and cobertura
                and cobertura.docente_id == current_user.id):
            visibles.append(ajuste)
    return visibles


def _registro(orm, campos: tuple[str, ...]) -> Optional[dict]:
    if orm is None:
        return None
    return {campo: getattr(orm, campo, None) for campo in campos}


def _datos_completitud(piar: PiarORM) -> PiarCompletitudData:
    estudiante = piar.estudiante
    salud = estudiante.entorno_salud
    hogar = estudiante.entorno_hogar
    trayectoria = estudiante.trayectoria_educativa
    matricula = estudiante.matricula_actual
    caracteristicas = piar.caracteristicas
    acta = piar.acta_acuerdo
    general = _registro(estudiante, (
            "nombres", "apellidos", "tipo_documento", "numero_documento",
            "fecha_nacimiento", "grupo_id", "lugar_nacimiento",
            "departamento_residencia", "municipio_residencia", "direccion",
            "barrio_vereda", "en_centro_proteccion", "centro_proteccion_donde",
            "pertenece_grupo_etnico", "grupo_etnico", "victima_conflicto",
            "registro_victima",
        )) or {}
    general["lugar_diligenciamiento"] = piar.lugar_diligenciamiento
    return PiarCompletitudData(
        general=general,
        salud=_registro(salud, (
            "afiliacion_salud", "eps", "regimen", "lugar_emergencias",
            "atendido_sector_salud", "atenciones_medicas", "tiene_diagnostico_medico",
            "diagnostico_medico", "asiste_terapias", "terapias_detalle",
            "consume_medicamentos", "medicamentos_lista", "medicamentos_detalle",
            "productos_apoyo_movilidad", "productos_apoyo_cual",
        )),
        hogar=_registro(hogar, (
            "nombre_madre", "nombre_padre", "nombre_cuidador", "acudiente_principal",
            "personas_vive_estudiante", "apoyo_crianza", "numero_hermanos",
        )),
        trayectoria=_registro(trayectoria, (
            "vinculado_sistema_anterior", "vinculado_educacion_inicial",
            "educacion_inicial_instituciones", "ultimo_grado_cursado",
            "estado_ultimo_grado", "recibe_informe_pedagogico",
            "institucion_procedencia_informe", "asiste_programas_complementarios",
            "programas_complementarios_cuales",
        )),
        matricula=_registro(matricula, ("institucion_educativa", "sede", "grado_ingreso", "jornada")),
        caracteristicas=_registro(caracteristicas, (
            "descripcion_gustos_intereses", "descripcion_habilidades",
            "caracterizacion_pedagogica", "expectativas_estudiante",
            "expectativas_familia", "redes_apoyo", "entorno_familiar_social_economico",
            "otras_observaciones",
        )),
        participantes=[
            _registro(p, ("nombre", "cargo", "area", "rol_piar", "confirmado")) or {}
            for p in piar.participantes
        ],
        asignaturas=[
            _registro(a, (
                "asignatura_id", "nombre_asignatura", "area_nombre", "docente_id",
                "docente_nombre", "estado", "justificacion",
            )) or {}
            for a in piar.asignaturas_estado
        ],
        ajustes=[
            _registro(a, (
                "asignatura_id", "area", "objetivos_propositos", "barreras_evidenciadas",
                "tipo_ajuste", "apoyo_requerido", "ajustes_estrategias", "temporalidad",
                "responsable", "medios_verificacion",
            )) or {}
            for a in piar.ajustes_razonables
        ],
        acta=_registro(acta, (
            "fecha_firma", "compromisos_aula", "firmado_estudiante",
            "firmado_acudiente", "firmado_docente_apoyo", "firmado_docentes_aula",
            "firmado_directivo",
        )),
        compromisos_casa=[
            _registro(c, ("nombre_actividad", "descripcion_estrategia", "frecuencia")) or {}
            for c in (acta.compromisos_casa if acta else [])
        ],
    )


def _evaluar_completitud(piar: PiarORM):
    return EvaluarCompletitudPiarUseCase().execute(_datos_completitud(piar))


def _respuesta_completitud(piar: PiarORM) -> PiarCompletitudResponse:
    resultado = _evaluar_completitud(piar)
    asignaturas = [PiarAsignaturaResponse.model_validate(a) for a in piar.asignaturas_estado]
    return PiarCompletitudResponse(
        porcentaje=resultado.porcentaje,
        completa=resultado.completa,
        puede_exportar_final=resultado.completa,
        secciones=[
            PiarSeccionCompletitud(
                codigo=seccion.codigo,
                nombre=seccion.nombre,
                completa=seccion.completa,
                faltantes=list(seccion.faltantes),
            )
            for seccion in resultado.secciones
        ],
        asignaturas=asignaturas,
    )


def _snapshot_piar(piar: PiarORM) -> dict:
    """Instantánea JSON reproducible; excluye soportes médicos y evidencias binarias."""
    data = _datos_completitud(piar)

    def normalizar(valor):
        if isinstance(valor, (date,)):
            return valor.isoformat()
        if isinstance(valor, uuid.UUID):
            return str(valor)
        if isinstance(valor, dict):
            return {k: normalizar(v) for k, v in valor.items()}
        if isinstance(valor, (list, tuple)):
            return [normalizar(v) for v in valor]
        return valor

    return normalizar({
        "formato": "MEN-PIAR-V15-08-2020",
        "piar_id": piar.id,
        "estudiante_id": piar.estudiante_id,
        "anio_lectivo": piar.anio_lectivo,
        "fecha_creacion": piar.fecha_creacion,
        "lugar_diligenciamiento": piar.lugar_diligenciamiento,
        "general": dict(data.general),
        "salud": dict(data.salud or {}),
        "hogar": dict(data.hogar or {}),
        "trayectoria": dict(data.trayectoria or {}),
        "matricula": dict(data.matricula or {}),
        "caracteristicas": dict(data.caracteristicas or {}),
        "participantes": list(data.participantes),
        "asignaturas": list(data.asignaturas),
        "ajustes": [serializar_ajuste(a) for a in piar.ajustes_razonables],
        "acta": dict(data.acta or {}),
        "compromisos_casa": list(data.compromisos_casa),
    })


async def _contexto_pdf(db: AsyncSession, piar: PiarORM):
    """Carga configuración y periodos relevantes para el documento oficial."""
    periodos_result = await db.execute(
        select(PeriodoAcademicoORM).order_by(PeriodoAcademicoORM.fecha_inicio)
    )
    periodos = periodos_result.scalars().all()
    ids_con_ajustes = {
        ajuste.periodo_id for ajuste in piar.ajustes_razonables if ajuste.periodo_id
    }
    hoy = date.today()
    seleccionados = [
        periodo for periodo in periodos
        if periodo.activo or periodo.fecha_inicio <= hoy or periodo.id in ids_con_ajustes
    ]
    config_result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    return config_result.scalars().first(), seleccionados


async def _generar_pdf_actual(
    db: AsyncSession,
    piar: PiarORM,
    modo: str,
    faltantes: Optional[list[str]] = None,
) -> bytes:
    from app.core.pdf_generator import generate_piar_oficial_pdf

    config, periodos = await _contexto_pdf(db, piar)
    return generate_piar_oficial_pdf(
        piar,
        config,
        periodos,
        modo=modo,
        faltantes=faltantes or [],
    )


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
            creador_nombre=f"{a.creador.nombre} {a.creador.apellido}" if a.creador else None,
            asignatura_id=a.asignatura_id,
            area=a.area,
            titulo_tema=a.titulo_tema,
            objetivos_propositos=a.objetivos_propositos,
            barreras_evidenciadas=a.barreras_evidenciadas,
            ajustes_estrategias=a.ajustes_estrategias,
            evaluacion_ajustes=a.evaluacion_ajustes,
            puntuacion=a.puntuacion,
            comentario_puntuacion=a.comentario_puntuacion,
            tipo_ajuste=a.tipo_ajuste,
            apoyo_requerido=a.apoyo_requerido,
            temporalidad=a.temporalidad,
            responsable=a.responsable,
            medios_verificacion=a.medios_verificacion,
            dba_referencia=a.dba_referencia,
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


def _texto_ia(valor) -> str:
    """Normaliza texto opcional para los prompts de IA; ignora vacíos y serializa JSON."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str) if valor else ""
    return str(valor).strip()


def construir_contexto_estudiante(piar, overrides: Optional[dict] = None) -> str:
    """Bloque de contexto del estudiante para los prompts de IA.

    Incluye los campos solicitados y omite con seguridad los que estén vacíos.
    `overrides` permite preferir lo que el docente editó en el formulario.
    """
    overrides = overrides or {}
    estudiante = getattr(piar, "estudiante", None)
    caracteristicas = getattr(piar, "caracteristicas", None)
    salud = getattr(estudiante, "entorno_salud", None) if estudiante else None

    def campo(fuente, atributo: str) -> str:
        return _texto_ia(getattr(fuente, atributo, None)) if fuente is not None else ""

    filas = [
        (
            "Gustos, intereses y expectativas del estudiante y su familia",
            " ".join(filter(None, (
                _texto_ia(overrides.get("gustos_intereses")) or campo(caracteristicas, "descripcion_gustos_intereses"),
                campo(caracteristicas, "expectativas_estudiante"),
                campo(caracteristicas, "expectativas_familia"),
            ))),
        ),
        (
            "Habilidades, cualidades, fortalezas y apoyos requeridos",
            " ".join(filter(None, (
                _texto_ia(overrides.get("habilidades_fortalezas")) or campo(caracteristicas, "descripcion_habilidades"),
                campo(caracteristicas, "redes_apoyo"),
            ))),
        ),
        ("Entorno familiar, social y económico",
         _texto_ia(overrides.get("entorno_familiar_social_economico")) or campo(caracteristicas, "entorno_familiar_social_economico")),
        ("Otras observaciones",
         _texto_ia(overrides.get("otras_observaciones")) or campo(caracteristicas, "otras_observaciones")),
        (
            "Caracterización pedagógica / Diagnóstico",
            _texto_ia(overrides.get("caracterizacion_pedagogica")) or campo(caracteristicas, "caracterizacion_pedagogica"),
        ),
        (
            "Diagnóstico médico",
            _texto_ia(overrides.get("diagnostico_medico")) or campo(salud, "diagnostico_medico"),
        ),
    ]
    lineas = [f"- {etiqueta}: {valor}" for etiqueta, valor in filas if valor]
    return "\n".join(lineas) if lineas else "- Sin información registrada."


def construir_contexto_institucional(config) -> str:
    """Bloque PEI/contexto institucional para los prompts de IA; tolera campos vacíos."""
    if config is None:
        return "Sin contexto institucional registrado."
    filas = [
        ("Modelo pedagógico del PEI", _texto_ia(getattr(config, "pei_modelo_pedagogico", None))),
        ("Valores y principios del PEI", _texto_ia(getattr(config, "pei_valores_principios", None))),
        ("Contexto institucional", _texto_ia(getattr(config, "contexto_institucion", None))),
    ]
    lineas = [f"- {etiqueta}: {valor}" for etiqueta, valor in filas if valor]
    return "\n".join(lineas) if lineas else "Sin contexto institucional registrado."


async def _configuracion_sistema(db: AsyncSession) -> Optional[ConfiguracionSistemaORM]:
    result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    return result.scalars().first()


@router.get("/estudiante/{estudiante_id}", response_model=PiarResponse)
async def get_piar_by_estudiante(
    estudiante_id: uuid.UUID,
    current_user: CurrentUser,
    anio: Optional[int] = Query(default=None, ge=2020),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el PIAR de un estudiante para el año indicado o el más reciente."""
    condiciones = [PiarORM.estudiante_id == estudiante_id]
    if anio is not None:
        condiciones.append(PiarORM.anio_lectivo == anio)
    query = (
        select(PiarORM)
        .where(*condiciones)
        .options(
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
            selectinload(PiarORM.caracteristicas),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.evidencias),
            selectinload(PiarORM.ajustes_razonables).selectinload(AjusteRazonableORM.creador),
            selectinload(PiarORM.acta_acuerdo).selectinload(ActaAcuerdoORM.compromisos_casa),
            selectinload(PiarORM.participantes),
            selectinload(PiarORM.asignaturas_estado),
            selectinload(PiarORM.versiones),
        )
        .order_by(PiarORM.created_at.desc())
    )
    result = await db.execute(query)
    piar = result.scalars().first()
    
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado para este estudiante.")

    director_nombre = None
    if piar.estudiante and piar.estudiante.grupo and piar.estudiante.grupo.director:
        d = piar.estudiante.grupo.director
        director_nombre = f"{d.nombre} {d.apellido}"

    response = PiarResponse.model_validate(piar)

    response.ajustes_razonables = _build_ajustes_response(_ajustes_visibles_para_usuario(piar, current_user))
    response.director_nombre = director_nombre

    return response

@router.post("/", response_model=PiarResponse)
async def create_piar(
    data: PiarCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Crea el PIAR anual y congela su carga académica inicial."""
    resultado_estudiante = await db.execute(
        select(EstudianteORM)
        .where(EstudianteORM.id == data.estudiante_id)
        .options(
            selectinload(EstudianteORM.grupo).selectinload(GrupoORM.sede),
            selectinload(EstudianteORM.grupo).selectinload(GrupoORM.director),
            selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.docente),
            selectinload(EstudianteORM.grupo).selectinload(GrupoORM.carga).selectinload(CargaAcademicaORM.asignatura).selectinload(AsignaturaORM.area),
        )
    )
    estudiante = resultado_estudiante.scalars().first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
    if not estudiante.grupo:
        raise HTTPException(status_code=409, detail="El estudiante debe tener un grupo asignado.")
    if not (current_user.rol.es_directivo or estudiante.grupo.director_id == current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Solo el director de grupo o un directivo puede iniciar el PIAR.",
        )

    existente = await db.execute(
        select(PiarORM).where(
            PiarORM.estudiante_id == data.estudiante_id,
            PiarORM.anio_lectivo == data.anio_lectivo,
        )
    )
    if existente.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un PIAR para el año {data.anio_lectivo}.",
        )

    cargas = estudiante.grupo.carga or []
    docentes_lista: list[str] = []
    for carga in cargas:
        nombre = f"{carga.docente.nombre} {carga.docente.apellido}"
        area = carga.asignatura.nombre
        docentes_lista.append(f"{nombre} ({area})")
    docentes = ", ".join(dict.fromkeys(docentes_lista)) or f"{current_user.nombre} {current_user.apellido}"
    nuevo_piar = PiarORM(
        estudiante_id=data.estudiante_id,
        anio_lectivo=data.anio_lectivo,
        estado="borrador",
        creado_por=current_user.id,
        docentes_elaboran=docentes,
        lugar_diligenciamiento=data.lugar_diligenciamiento or estudiante.grupo.sede.nombre,
    )
    db.add(nuevo_piar)
    await db.flush()

    orden = 0
    director = estudiante.grupo.director
    participantes_vistos: set[tuple[uuid.UUID, str]] = set()
    if director:
        db.add(PiarParticipanteORM(
            piar_id=nuevo_piar.id,
            usuario_id=director.id,
            nombre=f"{director.nombre} {director.apellido}",
            cargo=director.cargo,
            area=None,
            rol_piar="director_grupo",
            orden=orden,
            confirmado=True,
        ))
        orden += 1

    asignaturas_vistas: set[uuid.UUID] = set()
    for carga in cargas:
        docente = carga.docente
        asignatura = carga.asignatura
        clave_participante = (docente.id, asignatura.nombre)
        if clave_participante not in participantes_vistos:
            db.add(PiarParticipanteORM(
                piar_id=nuevo_piar.id,
                usuario_id=docente.id,
                nombre=f"{docente.nombre} {docente.apellido}",
                cargo=docente.cargo,
                area=asignatura.nombre,
                rol_piar="docente_aula",
                orden=orden,
                confirmado=True,
            ))
            participantes_vistos.add(clave_participante)
            orden += 1
        if asignatura.id not in asignaturas_vistas:
            db.add(PiarAsignaturaORM(
                piar_id=nuevo_piar.id,
                asignatura_id=asignatura.id,
                docente_id=docente.id,
                nombre_asignatura=asignatura.nombre,
                area_nombre=asignatura.area.nombre if asignatura.area else None,
                docente_nombre=f"{docente.nombre} {docente.apellido}",
                estado="pendiente",
            ))
            asignaturas_vistas.add(asignatura.id)

    if not estudiante.codigo_acceso_familia:
        import secrets
        estudiante.codigo_acceso_familia = secrets.token_hex(4)[:8]

    await registrar_cambio(
        db=db,
        entidad_tipo="piar_estado",
        entidad_id=nuevo_piar.id,
        piar_id=nuevo_piar.id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos={"estado": nuevo_piar.estado},
    )

    await db.flush()
    return await _cargar_piar_completo(db, nuevo_piar.id)

@router.post("/{piar_id}/ajustes", response_model=AjusteRazonableResponse)
async def add_ajuste_razonable(
    piar_id: uuid.UUID,
    data: AjusteRazonableCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Agrega un ajuste razonable a un PIAR asociándolo al periodo académico activo."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    _exigir_piar_editable(piar)
    cobertura = _buscar_cobertura_asignatura(piar, data.asignatura_id, data.area)
    if not cobertura:
        raise HTTPException(
            status_code=422,
            detail="La asignatura no pertenece a la carga académica congelada del PIAR.",
        )
    _exigir_permiso_asignatura(cobertura, current_user)

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
        asignatura_id=cobertura.asignatura_id,
        area=cobertura.nombre_asignatura,
        titulo_tema=data.titulo_tema,
        objetivos_propositos=data.objetivos_propositos,
        barreras_evidenciadas=data.barreras_evidenciadas,
        ajustes_estrategias=data.ajustes_estrategias,
        evaluacion_ajustes=data.evaluacion_ajustes,
        tipo_ajuste=data.tipo_ajuste,
        apoyo_requerido=data.apoyo_requerido,
        temporalidad=data.temporalidad,
        responsable=data.responsable,
        medios_verificacion=data.medios_verificacion,
        dba_referencia=data.dba_referencia,
    )
    db.add(nuevo_ajuste)
    cobertura.estado = "con_ajuste"
    cobertura.justificacion = None
    await db.flush()

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
        # Verificar PIAR (con contexto completo del estudiante)
        piar = await _cargar_piar_completo(db, piar_id)
        if not piar:
            raise HTTPException(status_code=404, detail="PIAR no encontrado.")

        config = await _configuracion_sistema(db)
        contexto_estudiante = construir_contexto_estudiante(piar)
        contexto_institucional = construir_contexto_institucional(config)

        # Construir Prompt
        prompt = (
            f"Actúa como un experto en Educación Inclusiva y Diseño Universal para el Aprendizaje (DUA).\n"
            f"Necesito sugerencias de estrategias y ajustes razonables concretos para un estudiante.\n\n"
            f"Contexto de la asignatura:\n"
            f"- Área/Materia: {data.area}\n"
        )
        if data.titulo_tema:
            prompt += f"- Título del Tema: {data.titulo_tema}\n"
        prompt += (
            f"- Objetivos o Propósitos de Aprendizaje: {data.objetivos_propositos}\n"
            f"- Barreras Evidenciadas en el Estudiante: {data.barreras_evidenciadas}\n"
            f"\nContexto del estudiante:\n{contexto_estudiante}\n"
            f"\nContexto institucional (PEI):\n{contexto_institucional}\n"
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
        # Verificar PIAR (con contexto completo del estudiante)
        piar = await _cargar_piar_completo(db, piar_id)
        if not piar:
            raise HTTPException(status_code=404, detail="PIAR no encontrado.")

        # --- Contexto institucional (PEI) y perfil ampliado del estudiante ---
        config = await _configuracion_sistema(db)
        contexto_institucional = construir_contexto_institucional(config)
        tiene_contexto_institucional = contexto_institucional != "Sin contexto institucional registrado."

        overrides = {
            "diagnostico_medico": data.diagnostico_medico,
            "gustos_intereses": data.gustos_intereses,
            "habilidades_fortalezas": data.habilidades_fortalezas,
            "caracterizacion_pedagogica": data.caracterizacion_pedagogica,
            "entorno_familiar_social_economico": data.entorno_familiar_social_economico,
            "otras_observaciones": data.otras_observaciones,
        }
        perfil_parts = []
        if data.estudiante_nombre:
            perfil_parts.append(f"Nombre: {data.estudiante_nombre}")
        if data.edad is not None:
            perfil_parts.append(f"Edad: {data.edad} años")
        if data.grado:
            perfil_parts.append(f"Grado escolar: {data.grado}")
        perfil_parts.append(construir_contexto_estudiante(piar, overrides))
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
OBJETIVOS / PROPÓSITOS DE APRENDIZAJE: {data.objetivos_propositos if data.objetivos_propositos else 'No especificados'}

PERFIL DEL ESTUDIANTE:
{perfil_texto}

BARRERAS IDENTIFICADAS POR EL DOCENTE EN ESTE CONTEXTO:
{data.barreras_evidenciadas}

REFERENCIA CURRICULAR (para contexto de los ajustes):
{curricular_texto}{instrucciones_extra}
{("""
CONTEXTO INSTITUCIONAL (PEI):
""" + contexto_institucional + """

IMPORTANTE SOBRE EL CONTEXTO INSTITUCIONAL: Los ajustes razonables que propongas deben ser realistas y viables dentro del contexto real de esta institución. No sugieras recursos tecnológicos, infraestructura, personal especializado o apoyos externos que no estén disponibles en este entorno específico. Por ejemplo: si la institución es rural y tiene conectividad limitada, no propongas estrategias que dependan de internet de alta velocidad, laboratorios especializados o equipos sofisticados. Adapta tus sugerencias a los recursos y posibilidades reales del entorno escolar descrito.
""") if tiene_contexto_institucional else ""}

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
- Escribe en tercera persona o imperativo (ej: "Presentar la información...", "El estudiante requiere...").
- En 'tipo_ajuste', clasifica el tipo principal de ajuste razonable (facilitador) entre: Didácticas (metodología), Recursos o materiales, Evaluación diferenciada, Tiempo adicional, Estrategias de enseñanza, u otro pertinente.
- En 'apoyo_requerido', detalla los apoyos categorizados por: Talento humano, Técnico, Tecnológico, Comunicativo. Cada categoría en una oración separada con punto y aparte. Solo menciona las categorías que realmente apliquen al caso."""

        # --- Esquema JSON para structured output ---
        schema_json = {
            "type": "object",
            "properties": {
                "ajustes_estrategias": {
                    "type": "string",
                    "description": "Ajustes razonables y estrategias DUA propuestos. Texto plano, consolidado, sin listas ni markdown. Cada ajuste separado con punto y aparte."
                },
                "tipo_ajuste": {
                    "type": "string",
                    "description": "Tipo de ajuste razonable (facilitador). Ej: 'Didácticas (metodología)', 'Recursos o materiales', 'Evaluación diferenciada'. Una frase corta."
                },
                "apoyo_requerido": {
                    "type": "string",
                    "description": "Apoyo requerido categorizado. Ej: 'Talento humano: docente de aula, orientador. Técnico: guías paso a paso, tablas impresas. Tecnológico: software PhET. Comunicativo: lenguaje sencillo, organizadores gráficos.'"
                }
            },
            "required": ["ajustes_estrategias", "tipo_ajuste", "apoyo_requerido"]
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
            ajustes_estrategias=parsed.get("ajustes_estrategias", "").strip(),
            tipo_ajuste=parsed.get("tipo_ajuste", "").strip() or None,
            apoyo_requerido=parsed.get("apoyo_requerido", "").strip() or None,
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
    """Actualiza parcialmente la caracterización y metadatos del PIAR."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    await _exigir_director_o_directivo(piar, current_user, db)
    _exigir_piar_editable(piar)
    if data.estado == "firmado":
        raise HTTPException(
            status_code=409,
            detail="Use el endpoint de finalización para validar y versionar el PIAR.",
        )

    estado_anterior = piar.estado
    carac_anteriores = serializar_caracteristicas(piar.caracteristicas) if piar.caracteristicas else None

    if data.estado is not None:
        piar.estado = data.estado

    if data.docentes_elaboran is not None:
        piar.docentes_elaboran = data.docentes_elaboran
    if data.lugar_diligenciamiento is not None:
        piar.lugar_diligenciamiento = data.lugar_diligenciamiento

    if data.caracteristicas is not None:
        if piar.caracteristicas:
            piar.caracteristicas.descripcion_gustos_intereses = data.caracteristicas.descripcion_gustos_intereses
            piar.caracteristicas.descripcion_habilidades = data.caracteristicas.descripcion_habilidades
            piar.caracteristicas.caracterizacion_pedagogica = data.caracteristicas.caracterizacion_pedagogica
            piar.caracteristicas.expectativas_estudiante = data.caracteristicas.expectativas_estudiante
            piar.caracteristicas.expectativas_familia = data.caracteristicas.expectativas_familia
            piar.caracteristicas.redes_apoyo = data.caracteristicas.redes_apoyo
            piar.caracteristicas.entorno_familiar_social_economico = data.caracteristicas.entorno_familiar_social_economico
            piar.caracteristicas.otras_observaciones = data.caracteristicas.otras_observaciones
        else:
            nueva_carac = CaracteristicasEstudianteORM(
                piar_id=piar.id,
                descripcion_gustos_intereses=data.caracteristicas.descripcion_gustos_intereses,
                descripcion_habilidades=data.caracteristicas.descripcion_habilidades,
                caracterizacion_pedagogica=data.caracteristicas.caracterizacion_pedagogica,
                expectativas_estudiante=data.caracteristicas.expectativas_estudiante,
                expectativas_familia=data.caracteristicas.expectativas_familia,
                redes_apoyo=data.caracteristicas.redes_apoyo,
                entorno_familiar_social_economico=data.caracteristicas.entorno_familiar_social_economico,
                otras_observaciones=data.caracteristicas.otras_observaciones,
            )
            db.add(nueva_carac)
            piar.caracteristicas = nueva_carac

    await db.flush()

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

    return await _cargar_piar_completo(db, piar_id)

@router.put("/{piar_id}/ajustes/{ajuste_id}", response_model=AjusteRazonableResponse)
async def update_ajuste_razonable(
    piar_id: uuid.UUID,
    ajuste_id: uuid.UUID,
    data: AjusteRazonableCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Modifica un ajuste razonable existente en la matriz."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    _exigir_piar_editable(piar)
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    cobertura_anterior = _buscar_cobertura_asignatura(piar, ajuste.asignatura_id, ajuste.area)
    if not cobertura_anterior:
        raise HTTPException(status_code=422, detail="El ajuste debe vincularse a una asignatura del PIAR.")
    _exigir_permiso_asignatura(cobertura_anterior, current_user)
    cobertura = _buscar_cobertura_asignatura(
        piar, data.asignatura_id or ajuste.asignatura_id, data.area
    )
    if not cobertura:
        raise HTTPException(status_code=422, detail="La asignatura no pertenece al PIAR.")
    _exigir_permiso_asignatura(cobertura, current_user)

    datos_antes = serializar_ajuste(ajuste)

    ajuste.asignatura_id = cobertura.asignatura_id
    ajuste.area = cobertura.nombre_asignatura
    ajuste.titulo_tema = data.titulo_tema
    ajuste.objetivos_propositos = data.objetivos_propositos
    ajuste.barreras_evidenciadas = data.barreras_evidenciadas
    ajuste.ajustes_estrategias = data.ajustes_estrategias
    ajuste.evaluacion_ajustes = data.evaluacion_ajustes
    ajuste.tipo_ajuste = data.tipo_ajuste
    ajuste.apoyo_requerido = data.apoyo_requerido
    ajuste.temporalidad = data.temporalidad
    ajuste.responsable = data.responsable
    ajuste.medios_verificacion = data.medios_verificacion
    ajuste.dba_referencia = data.dba_referencia

    cobertura.estado = "con_ajuste"
    cobertura.justificacion = None
    await db.flush()
    if cobertura_anterior and cobertura_anterior.asignatura_id != cobertura.asignatura_id:
        otros = await db.execute(
            select(AjusteRazonableORM.id).where(
                AjusteRazonableORM.piar_id == piar_id,
                AjusteRazonableORM.asignatura_id == cobertura_anterior.asignatura_id,
                AjusteRazonableORM.id != ajuste.id,
            ).limit(1)
        )
        if otros.scalar_one_or_none() is None:
            cobertura_anterior.estado = "pendiente"
            cobertura_anterior.justificacion = None

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
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    _exigir_piar_editable(piar)
    ajuste = await db.get(AjusteRazonableORM, ajuste_id)
    if not ajuste or ajuste.piar_id != piar_id:
        raise HTTPException(status_code=404, detail="Ajuste razonable no encontrado en este PIAR.")

    cobertura = _buscar_cobertura_asignatura(piar, ajuste.asignatura_id, ajuste.area)
    if cobertura:
        _exigir_permiso_asignatura(cobertura, current_user)

    datos_antes = serializar_ajuste(ajuste)
    ajuste_id = ajuste.id

    await db.delete(ajuste)
    await db.flush()

    if cobertura:
        restantes = await db.execute(
            select(AjusteRazonableORM.id).where(
                AjusteRazonableORM.piar_id == piar_id,
                AjusteRazonableORM.asignatura_id == cobertura.asignatura_id,
            ).limit(1)
        )
        if restantes.scalar_one_or_none() is None:
            cobertura.estado = "pendiente"
            cobertura.justificacion = None

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


@router.get("/{piar_id}/completitud", response_model=PiarCompletitudResponse)
async def get_completitud_piar(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el checklist oficial y la cobertura de la carga académica."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    return _respuesta_completitud(piar)


@router.patch(
    "/{piar_id}/asignaturas/{asignatura_id}",
    response_model=PiarAsignaturaResponse,
)
async def update_estado_asignatura(
    piar_id: uuid.UUID,
    asignatura_id: uuid.UUID,
    data: PiarAsignaturaEstadoUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Resuelve una asignatura sin ajuste o la devuelve a estado pendiente."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    _exigir_piar_editable(piar)
    cobertura = _buscar_cobertura_asignatura(piar, asignatura_id, "")
    if not cobertura:
        raise HTTPException(status_code=404, detail="Asignatura no incluida en este PIAR.")
    _exigir_permiso_asignatura(cobertura, current_user)

    justificacion = (data.justificacion or "").strip()
    if data.estado == "no_requiere" and len(justificacion) < 5:
        raise HTTPException(
            status_code=422,
            detail="La opción 'no requiere' exige una justificación de al menos 5 caracteres.",
        )
    cobertura.estado = data.estado
    cobertura.justificacion = justificacion if data.estado == "no_requiere" else None
    await db.flush()
    return cobertura


@router.get("/{piar_id}/pdf")
async def download_piar_pdf(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    modo: str = Query(default="borrador", pattern="^(borrador|final)$"),
    db: AsyncSession = Depends(get_db),
):
    """Descarga un borrador vivo o la última versión final inmutable."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")

    if modo == "final":
        versiones = sorted(piar.versiones, key=lambda item: item.numero)
        if not versiones:
            completitud = _respuesta_completitud(piar)
            raise HTTPException(
                status_code=409,
                detail={
                    "mensaje": "El PIAR debe finalizarse antes de descargar el PDF final.",
                    "completitud": completitud.model_dump(mode="json"),
                },
            )
        version = versiones[-1]
        contenido = version.pdf_archivo
        sufijo = f"v{version.numero}"
    else:
        resultado = _evaluar_completitud(piar)
        faltantes = [
            f"{seccion.nombre}: {', '.join(seccion.faltantes)}"
            for seccion in resultado.secciones if not seccion.completa
        ]
        contenido = await _generar_pdf_actual(db, piar, "borrador", faltantes)
        sufijo = "BORRADOR"

    filename = f"PIAR_{piar.estudiante.numero_documento}_{piar.anio_lectivo}_{sufijo}.pdf"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{piar_id}/finalizar", response_model=PiarVersionResponse)
async def finalizar_piar(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Valida el PIAR y conserva una versión final inmutable con su huella SHA-256."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    await _exigir_director_o_directivo(piar, current_user, db)
    if piar.estado == "firmado":
        raise HTTPException(status_code=409, detail="El PIAR ya está finalizado.")

    completitud = _evaluar_completitud(piar)
    try:
        numero = FinalizarPiarUseCase().execute(completitud, piar.version_actual)
    except PiarIncompletoError:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "El PIAR aún tiene información pendiente.",
                "completitud": _respuesta_completitud(piar).model_dump(mode="json"),
            },
        )

    pdf = await _generar_pdf_actual(db, piar, "final")
    snapshot = _snapshot_piar(piar)
    snapshot.update({"estado": "firmado", "version": numero})
    version_data = VersionarPiarUseCase().execute(numero, snapshot, pdf)
    version = PiarVersionORM(
        piar_id=piar.id,
        numero=version_data.numero,
        snapshot=dict(version_data.snapshot),
        pdf_archivo=version_data.pdf,
        sha256=version_data.sha256,
        creado_por=current_user.id,
    )
    db.add(version)
    piar.version_actual = numero
    piar.estado = "firmado"
    await db.flush()
    await registrar_cambio(
        db=db,
        entidad_tipo="piar_version",
        entidad_id=version.id,
        piar_id=piar.id,
        accion="crear",
        usuario_id=current_user.id,
        datos_nuevos={"numero": numero, "sha256": version.sha256},
    )
    return version


@router.post("/{piar_id}/reabrir", response_model=PiarResponse)
async def reabrir_piar(
    piar_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Reabre el PIAR conservando intactas sus versiones y reinicia confirmaciones."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    await _exigir_director_o_directivo(piar, current_user, db)
    if piar.estado != "firmado":
        raise HTTPException(status_code=409, detail="Solo puede reabrirse un PIAR finalizado.")

    piar.estado = ReabrirPiarUseCase().execute(piar.estado)
    if piar.acta_acuerdo:
        piar.acta_acuerdo.fecha_firma = None
        piar.acta_acuerdo.firmado_estudiante = False
        piar.acta_acuerdo.firmado_acudiente = False
        piar.acta_acuerdo.firmado_docente_apoyo = False
        piar.acta_acuerdo.firmado_docentes_aula = False
        piar.acta_acuerdo.firmado_directivo = False
    await db.flush()
    await registrar_cambio(
        db=db,
        entidad_tipo="piar_estado",
        entidad_id=piar.id,
        piar_id=piar.id,
        accion="modificar",
        usuario_id=current_user.id,
        datos_anteriores={"estado": "firmado", "version": piar.version_actual},
        datos_nuevos={"estado": "borrador", "version": piar.version_actual},
    )
    return await _cargar_piar_completo(db, piar_id)


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
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    await _exigir_director_o_directivo(piar, current_user, db)
    _exigir_piar_editable(piar)

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

    await db.flush()

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
    db: AsyncSession = Depends(get_db),
):
    """Alias compatible: entrega la versión final o un borrador si aún está abierto."""
    piar = await _cargar_piar_completo(db, piar_id)
    if not piar:
        raise HTTPException(status_code=404, detail="PIAR no encontrado.")
    versiones = sorted(piar.versiones, key=lambda item: item.numero)
    if piar.estado == "firmado" and versiones:
        pdf_bytes = versiones[-1].pdf_archivo
        sufijo = f"v{versiones[-1].numero}"
    else:
        resultado = _evaluar_completitud(piar)
        faltantes = [
            f"{seccion.nombre}: {', '.join(seccion.faltantes)}"
            for seccion in resultado.secciones if not seccion.completa
        ]
        pdf_bytes = await _generar_pdf_actual(db, piar, "borrador", faltantes)
        sufijo = "BORRADOR"
    filename = f"PIAR_{piar.estudiante.numero_documento}_{piar.anio_lectivo}_{sufijo}.pdf"
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
