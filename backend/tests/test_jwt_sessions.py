# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""JWT con claims, versión de sesión y refresh tokens con rotación."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    hash_refresh_token,
)
from app.domain.entities import Usuario
from app.domain.ports import IRefreshTokenRepository, RefreshTokenData
from app.entrypoints.api.dependencies import get_current_user
from app.use_cases.auth.change_password import ChangePasswordInput, ChangePasswordUseCase
from app.use_cases.auth.sessions import RefreshTokenInvalidoError, SesionService

USUARIO_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class InMemoryRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, RefreshTokenData] = {}

    async def create(
        self,
        *,
        usuario_id,
        token_hash,
        family_id,
        expires_at,
        user_agent=None,
        ip=None,
    ) -> RefreshTokenData:
        data = RefreshTokenData(
            id=uuid.uuid4(),
            usuario_id=usuario_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self._store[data.id] = data
        return data

    async def find_by_hash(self, token_hash) -> Optional[RefreshTokenData]:
        return next(
            (t for t in self._store.values() if t.token_hash == token_hash), None
        )

    async def update(self, token: RefreshTokenData) -> None:
        self._store[token.id] = token

    async def revoke_family(self, family_id) -> None:
        ahora = datetime.now(timezone.utc)
        for token in self._store.values():
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = ahora

    async def revoke_all_for_user(self, usuario_id) -> None:
        ahora = datetime.now(timezone.utc)
        for token in self._store.values():
            if token.usuario_id == usuario_id and token.revoked_at is None:
                token.revoked_at = ahora


class InMemoryUsuarioRepository:
    def __init__(self, usuario: Usuario):
        self._usuario = usuario

    async def find_by_id(self, user_id):
        return self._usuario if self._usuario.id == user_id else None

    async def find_by_email(self, email):
        return self._usuario

    async def save(self, usuario):
        self._usuario = usuario
        return usuario

    async def count(self):
        return 1


def _usuario(*, token_version: int = 0) -> Usuario:
    usuario = Usuario.crear(
        email="docente@colegio.edu.co",
        password_hash=get_password_hash("Segura123!"),
        nombre="Ada",
        apellido="Lovelace",
        rol="docente_aula",
        cargo=None,
    )
    usuario.id = USUARIO_ID
    usuario.token_version = token_version
    return usuario


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------

def test_access_token_incluye_claims_y_valida():
    token = create_access_token(subject=str(USUARIO_ID), token_version=3)
    claims = decode_access_token(token)

    assert claims is not None
    assert claims["sub"] == str(USUARIO_ID)
    assert claims["ver"] == 3
    assert claims["type"] == "access"
    assert claims["jti"]
    assert claims["iss"] and claims["aud"]


def test_decode_rechaza_firma_manipulada():
    token = create_access_token(subject=str(USUARIO_ID))
    manipulado = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    assert decode_access_token(manipulado) is None


def test_decode_rechaza_token_expirado():
    token = create_access_token(
        subject=str(USUARIO_ID),
        expires_delta=timedelta(seconds=-5),
    )
    assert decode_access_token(token) is None


def test_decode_rechaza_tipo_incorrecto(monkeypatch):
    from jose import jwt
    from app.core.config import get_settings

    settings = get_settings()
    payload = {
        "sub": str(USUARIO_ID),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "refresh",
        "ver": 0,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


def test_decode_rechaza_emisor_incorrecto(monkeypatch):
    from jose import jwt
    from app.core.config import get_settings

    settings = get_settings()
    payload = {
        "sub": str(USUARIO_ID),
        "iss": "otro-emisor",
        "aud": settings.JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "access",
        "ver": 0,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


# ---------------------------------------------------------------------------
# Versión de sesión
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_acepta_version_vigente():
    usuario = _usuario(token_version=1)
    repo = InMemoryUsuarioRepository(usuario)
    token = create_access_token(subject=str(USUARIO_ID), token_version=1)

    resultado = await get_current_user(token=token, repo=repo)

    assert resultado.id == USUARIO_ID


@pytest.mark.asyncio
async def test_get_current_user_rechaza_version_revocada():
    usuario = _usuario(token_version=2)
    repo = InMemoryUsuarioRepository(usuario)
    token = create_access_token(subject=str(USUARIO_ID), token_version=1)

    with pytest.raises(HTTPException) as error:
        await get_current_user(token=token, repo=repo)

    assert error.value.status_code == 401


# ---------------------------------------------------------------------------
# Sesiones con rotación
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rotacion_revoca_el_refresh_anterior():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw = await servicio.crear(USUARIO_ID)
    usuario_id, raw_nuevo = await servicio.rotar(raw)

    assert usuario_id == USUARIO_ID
    assert raw_nuevo != raw
    await servicio.rotar(raw_nuevo)
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw)


@pytest.mark.asyncio
async def test_reuso_inmediato_no_revoca_la_familia():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw = await servicio.crear(USUARIO_ID)
    _, raw_nuevo = await servicio.rotar(raw)

    # Reuso inmediato (carrera entre pestañas): no debe tumbar la familia.
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw)

    _, raw_nuevo_2 = await servicio.rotar(raw_nuevo)
    assert raw_nuevo_2


@pytest.mark.asyncio
async def test_reutilizacion_tardia_revoca_toda_la_familia():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw = await servicio.crear(USUARIO_ID)
    _, raw_nuevo = await servicio.rotar(raw)

    viejo = await repo.find_by_hash(hash_refresh_token(raw))
    viejo.revoked_at = datetime.now(timezone.utc) - timedelta(
        seconds=get_settings().REFRESH_REUSE_GRACE_SECONDS + 5
    )
    await repo.update(viejo)

    # Fuera de la gracia: se revoca la familia completa.
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw)
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw_nuevo)


@pytest.mark.asyncio
async def test_sesion_expira_a_las_24_horas():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw = await servicio.crear(USUARIO_ID)
    registro = await repo.find_by_hash(hash_refresh_token(raw))
    delta = registro.expires_at - datetime.now(timezone.utc)

    assert timedelta(hours=23, minutes=59) < delta <= timedelta(hours=24)


@pytest.mark.asyncio
async def test_refresh_expirado_no_se_puede_rotar():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw = await servicio.crear(USUARIO_ID)
    registro = await repo.find_by_hash(
        next(iter(repo._store.values())).token_hash
    )
    registro.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await repo.update(registro)

    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw)


@pytest.mark.asyncio
async def test_revocar_y_revocar_todo():
    repo = InMemoryRefreshTokenRepository()
    servicio = SesionService(repo)

    raw_a = await servicio.crear(USUARIO_ID)
    raw_b = await servicio.crear(USUARIO_ID)

    await servicio.revocar(raw_a)
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw_a)

    await servicio.revocar_todo(USUARIO_ID)
    with pytest.raises(RefreshTokenInvalidoError):
        await servicio.rotar(raw_b)


# ---------------------------------------------------------------------------
# Cambio de contraseña
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cambio_de_password_incrementa_version():
    usuario = _usuario(token_version=0)
    repo = InMemoryUsuarioRepository(usuario)

    await ChangePasswordUseCase(repo).execute(
        ChangePasswordInput(
            usuario_id=str(USUARIO_ID),
            current_password="Segura123!",
            new_password="NuevaSegura456!",
        )
    )

    assert usuario.token_version == 1
    assert usuario.password_hash != get_password_hash("Segura123!")
