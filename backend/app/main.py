# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Punto de entrada principal de OpenPiar — FastAPI Application.

Configura:
- CORS para el frontend Vue.js (localhost:5173 en dev)
- Middleware de Setup Guard (412 si no está configurado)
- Manejadores globales de excepciones de dominio
- Lifespan para inicializar la conexión a la BD
- Router v1 con todos los endpoints
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    CredencialesInvalidasError,
    EstudianteNoEncontradoError,
    EstudianteYaRegistradoError,
    OpenPiarException,
    SetupRequeridoError,
    SetupYaCompletadoError,
    UsuarioNoAutorizadoError,
    ValorObjetoInvalidoError,
)
from app.entrypoints.api.middleware import setup_guard_middleware
from app.entrypoints.api.v1.router import api_router

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO if settings.APP_ENV != "production" else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de ciclo de vida de la aplicación."""
    logger.info("🚀 OpenPiar iniciando en modo: %s", settings.APP_ENV)
    
    # Crear tablas si no existen al iniciar el servicio
    try:
        import app.adapters.db.models  # Registrar los modelos ORM en Base.metadata
        from app.adapters.db.session import Base, engine
        
        logger.info("Creando tablas en la base de datos si no existen...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tablas verificadas/creadas con éxito.")

        # Auto-sembrado de áreas y asignaturas si la tabla está vacía
        import uuid
        import json
        from pathlib import Path
        from sqlalchemy import select
        from app.adapters.db.session import AsyncSessionLocal
        from app.adapters.db.models import AreaORM, AsignaturaORM, ConfiguracionSistemaORM

        async with AsyncSessionLocal() as session:
            areas_exists = await session.execute(select(AreaORM).limit(1))
            if not areas_exists.scalars().first():
                logger.info("La tabla de áreas está vacía. Iniciando sembrado automático...")
                fixture_path = Path(__file__).parent / "fixtures" / "areas_asignaturas.json"
                if fixture_path.exists():
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Obtener ID de institución si existe
                    inst_result = await session.execute(select(ConfiguracionSistemaORM.id).limit(1))
                    inst_id = inst_result.scalar()
                    
                    for item in data:
                        area_nombre = item["area"]
                        asignaturas_nombres = item["asignaturas"]
                        
                        area = AreaORM(
                            id=uuid.uuid4(),
                            nombre=area_nombre,
                            institucion_id=inst_id
                        )
                        session.add(area)
                        
                        for asig_nombre in asignaturas_nombres:
                            asig = AsignaturaORM(
                                id=uuid.uuid4(),
                                nombre=asig_nombre,
                                area_id=area.id
                            )
                            session.add(asig)
                    
                    await session.commit()
                    logger.info("✅ Sembrado automático de %d áreas completado.", len(data))
                else:
                    logger.error("❌ No se encontró el archivo de fixtures en: %s", fixture_path)

    except Exception as exc:
        logger.error("Error intentando crear/sembrar tablas en el inicio: %s", exc)

    yield
    logger.info("🛑 OpenPiar cerrando.")


# ---------------------------------------------------------------------------
# Instancia FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OpenPiar API",
    description=(
        "API del Gestor de PIAR Comunitario Abierto para Colombia. "
        "Sistematiza el Plan Individual de Ajustes Razonables (Decreto 1421 de 2017) "
        "con un Agente Pedagógico de IA basado en el Diseño Universal para el Aprendizaje."
    ),
    version="0.1.0",
    contact={
        "name": "Comunidad OpenPiar",
        "url": "https://github.com/openpiar/openpiar",
    },
    license_info={
        "name": "GNU General Public License v3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
    docs_url="/docs" if settings.SHOW_DOCS else None,
    redoc_url="/redoc" if settings.SHOW_DOCS else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS — permite al frontend Vue.js (Vite) comunicarse con el backend
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Setup Guard Middleware
# ---------------------------------------------------------------------------

app.middleware("http")(setup_guard_middleware)


# ---------------------------------------------------------------------------
# Manejadores globales de excepciones de dominio
# ---------------------------------------------------------------------------

@app.exception_handler(EstudianteYaRegistradoError)
async def handle_estudiante_ya_registrado(
    request: Request, exc: EstudianteYaRegistradoError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(EstudianteNoEncontradoError)
async def handle_estudiante_no_encontrado(
    request: Request, exc: EstudianteNoEncontradoError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(CredencialesInvalidasError)
async def handle_credenciales_invalidas(
    request: Request, exc: CredencialesInvalidasError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(UsuarioNoAutorizadoError)
async def handle_no_autorizado(
    request: Request, exc: UsuarioNoAutorizadoError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)},
    )


@app.exception_handler(SetupRequeridoError)
async def handle_setup_requerido(
    request: Request, exc: SetupRequeridoError
) -> JSONResponse:
    return JSONResponse(
        status_code=412,
        content={"detail": str(exc), "setup_required": True},
    )


@app.exception_handler(SetupYaCompletadoError)
async def handle_setup_ya_completado(
    request: Request, exc: SetupYaCompletadoError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValorObjetoInvalidoError)
async def handle_valor_objeto_invalido(
    request: Request, exc: ValorObjetoInvalidoError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(OpenPiarException)
async def handle_openpiar_exception(
    request: Request, exc: OpenPiarException
) -> JSONResponse:
    """Manejador base para cualquier excepción de dominio no capturada antes."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Rutas de utilidad
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/health",
    tags=["Sistema"],
    summary="Health check",
    description="Verifica que la API está operativa.",
)
async def health_check() -> dict:
    return {
        "status": "ok",
        "app": "OpenPiar API",
        "version": "0.1.0",
        "env": settings.APP_ENV,
    }


# ---------------------------------------------------------------------------
# Incluir routers de la API v1
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")
