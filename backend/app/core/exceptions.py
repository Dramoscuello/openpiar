# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Excepciones de dominio de OpenPiar.
Cada excepción mapea a un código HTTP específico en los manejadores globales.
"""


class OpenPiarException(Exception):
    """Excepción base de dominio."""
    pass


# ---------------------------------------------------------------------------
# Dominio — Estudiantes / PIAR
# ---------------------------------------------------------------------------

class EstudianteYaRegistradoError(OpenPiarException):
    """Se intenta registrar un estudiante con documento ya existente."""
    pass


class EstudianteNoEncontradoError(OpenPiarException):
    """El estudiante solicitado no existe en la base de datos."""
    pass


class PiarNoEncontradoError(OpenPiarException):
    """El PIAR solicitado no existe."""
    pass


class PiarYaFirmadoError(OpenPiarException):
    """Se intenta modificar un PIAR que ya fue firmado."""
    pass


# ---------------------------------------------------------------------------
# Autenticación / Autorización
# ---------------------------------------------------------------------------

class CredencialesInvalidasError(OpenPiarException):
    """Email o contraseña incorrectos."""
    pass


class UsuarioNoAutorizadoError(OpenPiarException):
    """El usuario no tiene permisos para esta acción."""
    pass


class TokenInvalidoError(OpenPiarException):
    """El token JWT es inválido o ha expirado."""
    pass


# ---------------------------------------------------------------------------
# Setup / Configuración
# ---------------------------------------------------------------------------

class SetupRequeridoError(OpenPiarException):
    """La aplicación no ha completado el asistente de configuración inicial."""
    pass


class SetupYaCompletadoError(OpenPiarException):
    """Se intenta volver a ejecutar el setup en una instancia ya configurada."""
    pass


class ConexionBDFallidaError(OpenPiarException):
    """No se pudo establecer conexión con la base de datos durante el setup."""
    pass


# ---------------------------------------------------------------------------
# Valor Objetos
# ---------------------------------------------------------------------------

class ValorObjetoInvalidoError(OpenPiarException):
    """Un Value Object recibió un valor que viola sus invariantes."""
    pass
