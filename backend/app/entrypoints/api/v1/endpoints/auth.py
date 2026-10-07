# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de autenticación.
Ruta: /api/v1/auth/

Implementa OAuth2 Password Flow con access token de vida corta y refresh token
en cookie HttpOnly con rotación y detección de reutilización.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import CredencialesInvalidasError
from app.core.security import create_access_token
from app.entrypoints.api.dependencies import (
    CurrentUser,
    get_refresh_token_repo,
    get_usuario_repo,
)
from app.entrypoints.api.schemas import TokenResponse, UsuarioResponse, ChangePasswordRequest
from app.use_cases.auth.login import LoginInput, LoginUseCase
from app.use_cases.auth.sessions import RefreshTokenInvalidoError, SesionService
from app.adapters.db.session import get_db
from app.adapters.db.models import GrupoORM, UsuarioORM

router = APIRouter(prefix="/auth", tags=["Autenticación"])
settings = get_settings()

REFRESH_COOKIE = "openpiar_refresh"
COOKIE_PATH = "/api/v1/auth"


def _cookie_kwargs() -> dict:
    return {
        "key": REFRESH_COOKIE,
        "path": COOKIE_PATH,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE or "strict",
        "domain": settings.COOKIE_DOMAIN or None,
    }


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_cookie_kwargs(),
    )


def _limpiar_refresh_cookie(response: Response) -> None:
    response.delete_cookie(**_cookie_kwargs())


def _validar_origen(request: Request) -> None:
    """Defensa CSRF adicional: solo orígenes configurados pueden refrescar/firmar."""
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origen no permitido.",
        )


def _datos_cliente(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return user_agent, ip


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description=(
        "Autentica al docente/directivo y retorna un JWT de acceso de vida corta. "
        "Emite además un refresh token en cookie HttpOnly."
    ),
)
async def login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    repo=Depends(get_usuario_repo),
    refresh_repo=Depends(get_refresh_token_repo),
) -> TokenResponse:
    """Endpoint de login OAuth2. `username` se interpreta como email."""
    use_case = LoginUseCase(repo)
    try:
        result = await use_case.execute(
            LoginInput(email=form.username, password=form.password)
        )
    except CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_agent, ip = _datos_cliente(request)
    sesion = SesionService(refresh_repo)
    raw_refresh = await sesion.crear(
        result.usuario.id, user_agent=user_agent, ip=ip
    )
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=result.access_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar access token",
    description="Rota el refresh token y emite un nuevo access token.",
)
async def refresh_access_token(
    request: Request,
    response: Response,
    refresh_repo=Depends(get_refresh_token_repo),
    repo=Depends(get_usuario_repo),
) -> TokenResponse:
    _validar_origen(request)
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no encontrada.",
        )

    sesion = SesionService(refresh_repo)
    try:
        user_agent, ip = _datos_cliente(request)
        usuario_id, raw_nuevo = await sesion.rotar(
            raw_refresh, user_agent=user_agent, ip=ip
        )
    except RefreshTokenInvalidoError as exc:
        _limpiar_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = await repo.find_by_id(usuario_id)
    if not usuario:
        _limpiar_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )

    _set_refresh_cookie(response, raw_nuevo)
    return TokenResponse(
        access_token=create_access_token(
            subject=str(usuario.id),
            token_version=usuario.token_version,
        )
    )


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Revoca el refresh token actual y limpia la cookie de sesión.",
)
async def logout(
    request: Request,
    response: Response,
    refresh_repo=Depends(get_refresh_token_repo),
) -> dict:
    _validar_origen(request)
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    await SesionService(refresh_repo).revocar(raw_refresh)
    _limpiar_refresh_cookie(response)
    return {"message": "Sesión cerrada."}


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Usuario autenticado",
    description="Retorna la información del usuario autenticado con el token actual.",
)
async def get_me(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> UsuarioResponse:
    group_director_result = await db.execute(
        select(GrupoORM).where(GrupoORM.director_id == current_user.id)
    )
    es_director = group_director_result.scalars().first() is not None

    user_orm = await db.get(UsuarioORM, current_user.id)

    return UsuarioResponse(
        id=current_user.id,
        email=str(current_user.email),
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        rol=str(current_user.rol),
        es_director=es_director,
        tour_completado=user_orm.tour_completado if user_orm else False,
        created_at=current_user.created_at,
    )


@router.post(
    "/change-password",
    summary="Cambiar contraseña",
    description=(
        "Cambia la contraseña del usuario autenticado. Incrementa la versión de "
        "sesión y revoca todas las sesiones, incluida la actual."
    ),
)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current_user: CurrentUser,
    repo=Depends(get_usuario_repo),
    refresh_repo=Depends(get_refresh_token_repo),
) -> dict:
    from app.use_cases.auth.change_password import ChangePasswordInput, ChangePasswordUseCase
    use_case = ChangePasswordUseCase(repo)
    try:
        await use_case.execute(
            ChangePasswordInput(
                usuario_id=str(current_user.id),
                current_password=body.current_password,
                new_password=body.new_password,
            )
        )
    except CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    await SesionService(refresh_repo).revocar_todo(current_user.id)
    _limpiar_refresh_cookie(response)
    return {"message": "Contraseña actualizada. Inicia sesión de nuevo."}


@router.post(
    "/tour-completado",
    summary="Marcar tour como completado",
    description="Marca el tour guiado como completado para el usuario actual.",
)
async def mark_tour_completed(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    user_orm = await db.get(UsuarioORM, current_user.id)
    if not user_orm:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user_orm.tour_completado = True
    await db.commit()
    return {"tour_completado": True}
