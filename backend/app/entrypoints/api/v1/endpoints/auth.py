# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de autenticación.
Ruta: /api/v1/auth/

Implementa OAuth2 Password Flow compatible con el esquema estándar de FastAPI.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.exceptions import CredencialesInvalidasError
from app.entrypoints.api.dependencies import CurrentUser, get_usuario_repo
from app.entrypoints.api.schemas import TokenResponse, UsuarioResponse, ChangePasswordRequest
from app.use_cases.auth.login import LoginInput, LoginUseCase

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description=(
        "Autentica al docente/directivo y retorna un JWT Bearer token. "
        "Compatible con el formulario OAuth2 estándar (username=email, password)."
    ),
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    repo=Depends(get_usuario_repo),
) -> TokenResponse:
    """
    Endpoint de login OAuth2.
    `username` del formulario se interpreta como email.
    """
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

    return TokenResponse(access_token=result.access_token)


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Usuario autenticado",
    description="Retorna la información del usuario autenticado con el token actual.",
)
async def get_me(current_user: CurrentUser) -> UsuarioResponse:
    return UsuarioResponse(
        id=current_user.id,
        email=str(current_user.email),
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        rol=str(current_user.rol),
        created_at=current_user.created_at,
    )


@router.post(
    "/change-password",
    summary="Cambiar contraseña",
    description="Cambia la contraseña del usuario actualmente autenticado.",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    repo=Depends(get_usuario_repo),
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
    return {"message": "Contraseña actualizada exitosamente."}
