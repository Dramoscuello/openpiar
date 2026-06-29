# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Router principal v1 — agrega todos los sub-routers de la API.
"""

from fastapi import APIRouter

from app.entrypoints.api.v1.endpoints.auth import router as auth_router
from app.entrypoints.api.v1.endpoints.curriculum import router as curriculum_router
from app.entrypoints.api.v1.endpoints.directorio import router as directorio_router
from app.entrypoints.api.v1.endpoints.estudiantes import router as estudiantes_router
from app.entrypoints.api.v1.endpoints.setup import router as setup_router
from app.entrypoints.api.v1.endpoints.gestion_escolar import router as gestion_router
from app.entrypoints.api.v1.endpoints.piars import router as piars_router

api_router = APIRouter()

api_router.include_router(setup_router)
api_router.include_router(auth_router)
api_router.include_router(estudiantes_router)
api_router.include_router(curriculum_router)
api_router.include_router(directorio_router)
api_router.include_router(gestion_router)
api_router.include_router(piars_router)
