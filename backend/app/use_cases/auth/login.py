# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Casos de uso de autenticación:
- LoginUseCase: Valida credenciales y emite token JWT.
- RegistrarAdminUseCase: Crea el usuario administrador durante el Setup Wizard.
"""

from dataclasses import dataclass

from app.core.exceptions import CredencialesInvalidasError, SetupYaCompletadoError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domain.entities import Usuario
from app.domain.ports import IUsuarioRepository


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@dataclass
class LoginInput:
    email: str
    password: str


@dataclass
class LoginOutput:
    access_token: str
    token_type: str
    usuario: Usuario


class LoginUseCase:
    """Autentica un usuario y retorna un JWT Bearer token."""

    def __init__(self, usuario_repository: IUsuarioRepository) -> None:
        self._repo = usuario_repository

    async def execute(self, data: LoginInput) -> LoginOutput:
        usuario = await self._repo.find_by_email(data.email)

        if not usuario or not verify_password(data.password, usuario.password_hash):
            raise CredencialesInvalidasError(
                "Correo electrónico o contraseña incorrectos."
            )

        token = create_access_token(subject=str(usuario.id))
        return LoginOutput(
            access_token=token,
            token_type="bearer",
            usuario=usuario,
        )


# ---------------------------------------------------------------------------
# Registrar administrador inicial (Setup Wizard)
# ---------------------------------------------------------------------------

@dataclass
class RegistrarAdminInput:
    email: str
    password: str
    nombre: str
    apellido: str
    cargo: str


class RegistrarAdminUseCase:
    """
    Crea el primer usuario administrador (directivo) durante el Setup Wizard.
    Solo puede ejecutarse cuando no hay usuarios registrados.
    """

    def __init__(self, usuario_repository: IUsuarioRepository) -> None:
        self._repo = usuario_repository

    async def execute(self, data: RegistrarAdminInput) -> Usuario:
        # Validar fortaleza de la contraseña en el dominio
        from app.domain.entities import validar_password_fortaleza
        validar_password_fortaleza(data.password)

        total = await self._repo.count()
        if total > 0:
            raise SetupYaCompletadoError(
                "Ya existe un administrador registrado en el sistema."
            )

        usuario = Usuario.crear(
            email=data.email,
            password_hash=get_password_hash(data.password),
            nombre=data.nombre,
            apellido=data.apellido,
            rol="directivo",
            cargo=data.cargo,
        )
        return await self._repo.save(usuario)
