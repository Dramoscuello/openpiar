# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints del Setup Wizard (Módulo 0).

Ruta: /api/v1/setup/

El middleware de setup bloquea TODA la API si setup_completado = False,
excepto las rutas de este router.
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.adapters.db.models import ConfiguracionSistemaORM
from app.adapters.db.session import get_db
from app.core.config import settings
from app.core.exceptions import SetupYaCompletadoError
from app.core.gemini_crypto import encrypt_gemini_key
from app.core.gemini_privacy import sanitizar_texto_gemini
from app.adapters.ai.gemini_service import (
    GeminiQuotaError,
    GeminiServiceError,
    GeminiTimeoutError,
)
from app.entrypoints.api.dependencies import (
    get_usuario_repo,
    require_bootstrap_token,
    require_bootstrap_token_diagnostico,
)
from app.entrypoints.api.schemas import (
    ConfigurarSistemaRequest,
    SetupStatusResponse,
    TestDBResponse,
)
from app.use_cases.auth.login import RegistrarAdminInput, RegistrarAdminUseCase

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])
logger = logging.getLogger(__name__)

TIMEOUT_CONEXION_SEGUNDOS = 5


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
        "Verifica la conexión con el PostgreSQL configurado para OpenPiar "
        "(DB_HOST, DB_PORT, DB_NAME del servidor). No acepta hosts ni "
        "credenciales desde el cliente. Requiere el header X-Bootstrap-Token."
    ),
    dependencies=[Depends(require_bootstrap_token_diagnostico)],
)
async def test_database_connection() -> TestDBResponse:
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"timeout": TIMEOUT_CONEXION_SEGUNDOS},
    )

    async def _probar() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_probar(), timeout=TIMEOUT_CONEXION_SEGUNDOS)
        return TestDBResponse(success=True, message="Conexión exitosa a PostgreSQL.")
    except asyncio.TimeoutError:
        logger.warning(
            "Test DB agotó el tiempo de espera (%ss): host=%s port=%s db=%s",
            TIMEOUT_CONEXION_SEGUNDOS,
            settings.DB_HOST,
            settings.DB_PORT,
            settings.DB_NAME,
        )
        return TestDBResponse(
            success=False,
            message=(
                "Tiempo de espera agotado al conectar con PostgreSQL. "
                "Revisa los logs del servidor."
            ),
        )
    except Exception as exc:
        logger.warning(
            "Test DB falló (%s): host=%s port=%s db=%s",
            type(exc).__name__,
            settings.DB_HOST,
            settings.DB_PORT,
            settings.DB_NAME,
        )
        return TestDBResponse(
            success=False,
            message=(
                "No se pudo conectar con el PostgreSQL configurado. "
                "Revisa los logs del servidor."
            ),
        )
    finally:
        await engine.dispose()


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
        "Solo puede ejecutarse una vez y requiere el header X-Bootstrap-Token."
    ),
    dependencies=[Depends(require_bootstrap_token)],
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
    try:
        clave_gemini = (
            encrypt_gemini_key(body.gemini_api_key)
            if body.gemini_api_key and body.gemini_api_key.strip()
            else None
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo proteger la configuración de IA.",
        ) from exc

    config = ConfiguracionSistemaORM(
        nombre_institucion=body.nombre_institucion,
        nit=body.nit,
        codigo_dane=body.codigo_dane,
        direccion=body.direccion,
        telefono_contacto=body.telefono_contacto,
        correo_contacto=body.correo_contacto,
        nombre_rector=body.nombre_rector,
        gemini_api_key=clave_gemini,
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
        "institucionales y los devuelve al frontend. Requiere el header "
        "X-Bootstrap-Token."
    ),
    dependencies=[Depends(require_bootstrap_token)],
)
async def upload_pei(
    file: UploadFile,
    gemini_api_key: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> dict:
    import io
    import pdfplumber
    from app.adapters.ai.gemini_adapter import GeminiAgentAdapter
    from app.core.gemini_key import resolver_gemini_key

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo debe ser un PDF (.pdf).",
        )

    if not settings.AI_EXTERNAL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El procesamiento externo de IA está deshabilitado.",
        )

    llave_gemini = gemini_api_key.strip() or await resolver_gemini_key(db)
    if not llave_gemini:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se encontró la clave de API de Gemini. "
                "Configúrala en el asistente de configuración o en el archivo .env."
            ),
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

        # Llamar al agente Gemini con la API Key del formulario, la BD o el entorno
        agente = GeminiAgentAdapter(api_key=llave_gemini)
        perfil = await agente.extraer_perfil_pei(sanitizar_texto_gemini(texto, 8000))

        return {
            "message": "PEI procesado exitosamente.",
            "nombre_archivo": file.filename,
            "perfil_extraido": perfil
        }

    except GeminiQuotaError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="La cuota del servicio de IA está agotada. Intenta más tarde.",
            headers={"Retry-After": "60"},
        ) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="El servicio de IA tardó demasiado en responder.",
        ) from exc
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible procesar el PEI con el servicio de IA.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Error procesando PEI tipo=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible procesar el PEI en este momento.",
        ) from exc
