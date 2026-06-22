# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Tests unitarios del dominio — sin base de datos, sin IA, sin framework.

Demuestra la testabilidad de la arquitectura hexagonal:
los casos de uso se testean con repositorios en memoria.
"""

import uuid
from datetime import date
from typing import Optional

import pytest

from app.core.exceptions import EstudianteYaRegistradoError
from app.core.security import get_password_hash, verify_password
from app.domain.entities import Estudiante, Piar, Usuario
from app.domain.ports import IEstudianteRepository, IUsuarioRepository
from app.domain.value_objects import Email, Rol
from app.use_cases.auth.login import LoginInput, LoginUseCase, RegistrarAdminInput, RegistrarAdminUseCase
from app.use_cases.estudiantes.crear_estudiante import CrearEstudianteInput, CrearEstudianteUseCase


# ---------------------------------------------------------------------------
# Repositorios en memoria (adaptadores de test)
# ---------------------------------------------------------------------------

class InMemoryUsuarioRepository(IUsuarioRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, Usuario] = {}

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[Usuario]:
        return self._store.get(user_id)

    async def find_by_email(self, email: str) -> Optional[Usuario]:
        return next(
            (u for u in self._store.values() if str(u.email).lower() == email.lower()),
            None,
        )

    async def save(self, usuario: Usuario) -> Usuario:
        self._store[usuario.id] = usuario
        return usuario

    async def count(self) -> int:
        return len(self._store)


class InMemoryEstudianteRepository(IEstudianteRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, Estudiante] = {}

    async def find_by_id(self, estudiante_id: uuid.UUID) -> Optional[Estudiante]:
        return self._store.get(estudiante_id)

    async def find_by_documento(self, tipo: str, numero: str) -> Optional[Estudiante]:
        return next(
            (
                e for e in self._store.values()
                if e.tipo_documento == tipo and e.numero_documento == numero
            ),
            None,
        )

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Estudiante]:
        return list(self._store.values())[skip:skip + limit]

    async def save(self, estudiante: Estudiante) -> Estudiante:
        self._store[estudiante.id] = estudiante
        return estudiante

    async def count(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Tests — Value Objects
# ---------------------------------------------------------------------------

class TestValueObjects:
    def test_email_valido(self):
        email = Email("docente@colegio.edu.co")
        assert str(email) == "docente@colegio.edu.co"

    def test_email_invalido_sin_arroba(self):
        with pytest.raises(Exception):
            Email("no-es-un-email")

    def test_rol_valido(self):
        rol = Rol("docente_aula")
        assert rol.puede_crear_piar is True

    def test_rol_directivo_no_puede_crear_piar(self):
        rol = Rol("directivo")
        assert rol.es_directivo is True
        assert rol.puede_crear_piar is False

    def test_rol_invalido(self):
        with pytest.raises(Exception):
            Rol("superadmin")


# ---------------------------------------------------------------------------
# Tests — Entidades de dominio
# ---------------------------------------------------------------------------

class TestEntidades:
    def test_crear_usuario(self):
        usuario = Usuario.crear(
            email="rector@colegio.edu.co",
            password_hash="hash",
            nombre="Carlos",
            apellido="González",
            rol="directivo",
            cargo="Rector",
        )
        assert usuario.nombre_completo == "Carlos González"
        assert usuario.id is not None
        assert usuario.cargo == "Rector"

    def test_crear_estudiante(self):
        est = Estudiante.crear(
            nombres="María",
            apellidos="López",
            tipo_documento="TI",
            numero_documento="1234567890",
            fecha_nacimiento=date(2015, 5, 10),
            edad=9,
            departamento_residencia="Cundinamarca",
            municipio_residencia="Bogotá",
            direccion="Calle 1 #2-3",
            barrio_vereda="Los Pinos",
        )
        assert est.nombre_completo == "María López"

    def test_piar_transiciones_estado(self):
        piar = Piar.crear(
            estudiante_id=uuid.uuid4(),
            anio_lectivo=2026,
        )
        assert piar.estado == "borrador"
        assert piar.es_editable is True

        piar.marcar_generando_ia()
        assert piar.estado == "generando_ia"

        piar.marcar_en_revision()
        assert piar.estado == "en_revision"

        piar.firmar()
        assert piar.estado == "firmado"
        assert piar.es_editable is False

    def test_piar_no_puede_firmar_directo_desde_generando(self):
        piar = Piar.crear(estudiante_id=uuid.uuid4(), anio_lectivo=2026)
        piar.marcar_generando_ia()
        with pytest.raises(ValueError):
            piar.firmar()


# ---------------------------------------------------------------------------
# Tests — Casos de uso
# ---------------------------------------------------------------------------

class TestCrearEstudiante:
    @pytest.fixture
    def repo(self):
        return InMemoryEstudianteRepository()

    @pytest.fixture
    def use_case(self, repo):
        return CrearEstudianteUseCase(repo)

    async def test_crear_estudiante_exitoso(self, use_case):
        data = CrearEstudianteInput(
            nombres="Ana",
            apellidos="Pérez",
            tipo_documento="TI",
            numero_documento="987654321",
            fecha_nacimiento=date(2014, 3, 15),
            edad=10,
            departamento_residencia="Antioquia",
            municipio_residencia="Medellín",
            direccion="Carrera 50 #60-70",
            barrio_vereda="El Poblado",
        )
        estudiante = await use_case.execute(data)
        assert estudiante.nombres == "Ana"
        assert estudiante.id is not None

    async def test_no_permite_documento_duplicado(self, use_case):
        data = CrearEstudianteInput(
            nombres="Luis",
            apellidos="Martínez",
            tipo_documento="TI",
            numero_documento="111222333",
            fecha_nacimiento=date(2013, 7, 20),
            edad=11,
            departamento_residencia="Valle",
            municipio_residencia="Cali",
            direccion="Av. 1 #2-3",
            barrio_vereda="El Centro",
        )
        await use_case.execute(data)

        with pytest.raises(EstudianteYaRegistradoError):
            await use_case.execute(data)


class TestLogin:
    @pytest.fixture
    def repo(self):
        return InMemoryUsuarioRepository()

    async def test_login_exitoso(self, repo):
        # Crear usuario admin primero
        registrar = RegistrarAdminUseCase(repo)
        await registrar.execute(
            RegistrarAdminInput(
                email="admin@colegio.edu.co",
                password="SecurePassword123!",
                nombre="Admin",
                apellido="Test",
                cargo="Rector",
            )
        )

        # Login
        login = LoginUseCase(repo)
        result = await login.execute(
            LoginInput(email="admin@colegio.edu.co", password="SecurePassword123!")
        )
        assert result.access_token != ""
        assert result.token_type == "bearer"

    async def test_login_falla_con_password_incorrecto(self, repo):
        from app.core.exceptions import CredencialesInvalidasError

        registrar = RegistrarAdminUseCase(repo)
        await registrar.execute(
            RegistrarAdminInput(
                email="admin2@colegio.edu.co",
                password="Correcta123!",
                nombre="Admin",
                apellido="Test",
                cargo="Coordinador",
            )
        )

        login = LoginUseCase(repo)
        with pytest.raises(CredencialesInvalidasError):
            await login.execute(
                LoginInput(email="admin2@colegio.edu.co", password="incorrecta")
            )

    async def test_registro_admin_falla_con_contrasena_debil(self, repo):
        registrar = RegistrarAdminUseCase(repo)
        with pytest.raises(ValueError, match="La contraseña debe"):
            await registrar.execute(
                RegistrarAdminInput(
                    email="admin3@colegio.edu.co",
                    password="debil",
                    nombre="Admin",
                    apellido="Test",
                    cargo="Rector",
                )
            )

    async def test_registro_admin_falla_con_cargo_invalido(self, repo):
        from app.core.exceptions import ValorObjetoInvalidoError

        registrar = RegistrarAdminUseCase(repo)
        with pytest.raises(ValorObjetoInvalidoError, match="Cargo 'Superadmin' inválido"):
            await registrar.execute(
                RegistrarAdminInput(
                    email="admin4@colegio.edu.co",
                    password="SecurePassword123!",
                    nombre="Admin",
                    apellido="Test",
                    cargo="Superadmin",
                )
            )
