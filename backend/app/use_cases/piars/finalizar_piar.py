# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Regla de aplicación para autorizar el cierre de una versión PIAR."""

from __future__ import annotations

from dataclasses import dataclass

from .evaluar_completitud import ResultadoCompletitud


class PiarIncompletoError(ValueError):
    def __init__(self, resultado: ResultadoCompletitud) -> None:
        super().__init__("El PIAR todavía tiene información pendiente.")
        self.resultado = resultado


@dataclass(frozen=True)
class FinalizarPiarUseCase:
    """Autoriza la próxima versión únicamente cuando las siete secciones están completas."""

    def execute(self, completitud: ResultadoCompletitud, version_actual: int) -> int:
        if not completitud.completa:
            raise PiarIncompletoError(completitud)
        return version_actual + 1
