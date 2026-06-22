# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Caso de uso para cambio de contraseña de usuario.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.exceptions import CredencialesInvalidasError
from app.core.security import get_password_hash, verify_password
from app.domain.entities import Usuario, validar_password_fortaleza
from app.domain.ports import IUsuarioRepository


@dataclass
class ChangePasswordInput:
    usuario_id: str
    current_password: str
    new_password: str


class ChangePasswordUseCase:
    """Caso de uso que cambia la contraseña de un usuario validando la actual y la fortaleza de la nueva."""

    def __init__(self, usuario_repository: IUsuarioRepository) -> None:
        self._repo = usuario_repository

    async def execute(self, data: ChangePasswordInput) -> None:
        try:
            uid = uuid.UUID(data.usuario_id)
        except ValueError:
            raise CredencialesInvalidasError("ID de usuario inválido.")

        usuario = await self._repo.find_by_id(uid)
        if not usuario:
            raise CredencialesInvalidasError("Usuario no encontrado.")

        # Verificar la contraseña actual
        if not verify_password(data.current_password, usuario.password_hash):
            raise CredencialesInvalidasError("La contraseña actual es incorrecta.")

        # Validar la fortaleza de la nueva contraseña
        validar_password_fortaleza(data.new_password)

        # Hashear y actualizar
        usuario.password_hash = get_password_hash(data.new_password)
        usuario.updated_at = datetime.now(timezone.utc)

        await self._repo.save(usuario)
