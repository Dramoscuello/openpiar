# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints del Setup Wizard (Módulo 0).

Ruta: /api/v1/setup/

El middleware de setup bloquea TODA la API si setup_completado = False,
excepto las rutas de este router.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ConfiguracionSistemaORM
from app.adapters.db.session import get_db
from app.core.exceptions import SetupYaCompletadoError
from app.entrypoints.api.dependencies import get_usuario_repo
from app.entrypoints.api.schemas import (
    ConfigurarSistemaRequest,
    SetupStatusResponse,
    TestDBRequest,
    TestDBResponse,
)
from app.use_cases.auth.login import RegistrarAdminInput, RegistrarAdminUseCase

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /setup/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=SetupStatusResponse,
    summary="Estado del Setup Wizard",
    description=(
        "Consulta si la configuración inicial de OpenPiar fue completada. "
        "El frontend usa este endpoint en cada arranque para decidir si mostrar "
        "el Setup Wizard o la pantalla de login."
    ),
)
async def get_setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatusResponse:
    result = await db.execute(select(ConfiguracionSistemaORM).limit(1))
    config = result.scalars().first()

    if not config:
        return SetupStatusResponse(setup_completado=False)

    return SetupStatusResponse(
        setup_completado=config.setup_completado,
        nombre_institucion=config.nombre_institucion if config.setup_completado else None,
        tiene_gemini_key=bool(config.gemini_api_key),
    )


# ---------------------------------------------------------------------------
# POST /setup/test-db
# ---------------------------------------------------------------------------

@router.post(
    "/test-db",
    response_model=TestDBResponse,
    summary="Probar conexión a PostgreSQL",
    description=(
        "Verifica que las credenciales de PostgreSQL son correctas "
        "antes de guardarlas en la configuración."
    ),
)
async def test_database_connection(body: TestDBRequest) -> TestDBResponse:
    from sqlalchemy.ext.asyncio import create_async_engine

    test_url = (
        f"postgresql+asyncpg://{body.user}:{body.password}"
        f"@{body.host}:{body.port}/{body.database}"
    )
    try:
        test_engine = create_async_engine(test_url, echo=False)
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await test_engine.dispose()
        return TestDBResponse(success=True, message="Conexión exitosa a PostgreSQL.")
    except Exception as exc:
        logger.warning("Test DB fallido: %s", exc)
        return TestDBResponse(
            success=False,
            message=f"No se pudo conectar: {exc}",
        )


# ---------------------------------------------------------------------------
# POST /setup/configure
# ---------------------------------------------------------------------------

@router.post(
    "/configure",
    status_code=status.HTTP_201_CREATED,
    summary="Configurar institución y administrador inicial",
    description=(
        "Paso final del Setup Wizard. Registra los datos del colegio, "
        "la API Key de Gemini, y crea el usuario administrador (directivo). "
        "Solo puede ejecutarse una vez."
    ),
)
async def configurar_sistema(
    body: ConfigurarSistemaRequest,
    db: AsyncSession = Depends(get_db),
    usuario_repo=Depends(get_usuario_repo),
) -> dict:
    # Verificar que el setup no se ha completado antes
    result = await db.execute(
        select(ConfiguracionSistemaORM).where(
            ConfiguracionSistemaORM.setup_completado == True  # noqa: E712
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El sistema ya fue configurado. No se puede ejecutar el setup de nuevo.",
        )

    # Registrar administrador inicial
    try:
        registrar_admin = RegistrarAdminUseCase(usuario_repo)
        admin = await registrar_admin.execute(
            RegistrarAdminInput(
                email=body.admin_email,
                password=body.admin_password,
                nombre=body.admin_nombre,
                apellido=body.admin_apellido,
                cargo=body.admin_cargo,
            )
        )
    except SetupYaCompletadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Guardar configuración del sistema
    config = ConfiguracionSistemaORM(
        nombre_institucion=body.nombre_institucion,
        nit=body.nit,
        codigo_dane=body.codigo_dane,
        direccion=body.direccion,
        telefono_contacto=body.telefono_contacto,
        correo_contacto=body.correo_contacto,
        nombre_rector=body.nombre_rector,
        gemini_api_key=body.gemini_api_key,
        contexto_institucion=body.contexto_institucion,
        pei_nombre_archivo=body.pei_nombre_archivo,
        pei_modelo_pedagogico=body.pei_modelo_pedagogico,
        pei_valores_principios=body.pei_valores_principios,
        setup_completado=True,
    )
    db.add(config)
    await db.flush()

    logger.info(
        "Setup completado para institución '%s' por admin '%s'",
        body.nombre_institucion,
        admin.nombre_completo,
    )

    return {
        "message": "Configuración completada exitosamente.",
        "institucion": body.nombre_institucion,
        "admin_id": str(admin.id),
    }


# ---------------------------------------------------------------------------
# POST /setup/upload-pei
# ---------------------------------------------------------------------------

@router.post(
    "/upload-pei",
    summary="Subir PDF del PEI institucional",
    description=(
        "Sube el Proyecto Educativo Institucional en PDF. "
        "Gemini extrae sincrónicamente el modelo pedagógico y los valores "
        "institucionales y los devuelve al frontend."
    ),
)
async def upload_pei(
    file: UploadFile,
    gemini_api_key: str = Form(...),
) -> dict:
    import io
    import pdfplumber
    from app.adapters.ai.gemini_adapter import GeminiAgentAdapter

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo debe ser un PDF (.pdf).",
        )

    # Leer el PDF en memoria
    contenido = await file.read()
    if len(contenido) > 50 * 1024 * 1024:  # Límite 50 MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El PDF no puede superar 50 MB.",
        )

    try:
        # Extraer texto del PDF
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            texto = "\n".join(
                page.extract_text() or "" for page in pdf.pages[:30]  # Máx 30 páginas
            )

        if not texto.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se pudo extraer texto del PEI. Asegúrate de que no sea una imagen escaneada.",
            )

        # Llamar al agente Gemini con la API Key proporcionada
        agente = GeminiAgentAdapter(api_key=gemini_api_key)
        perfil = await agente.extraer_perfil_pei(texto)

        return {
            "message": "PEI procesado exitosamente.",
            "nombre_archivo": file.filename,
            "perfil_extraido": perfil
        }

    except Exception as exc:
        logger.error("Error procesando PEI: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al analizar el PEI con IA: {str(exc)}"
        )
