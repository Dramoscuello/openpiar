# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Regla pura para reabrir una versión PIAR ya finalizada."""


class ReabrirPiarUseCase:
    def execute(self, estado_actual: str) -> str:
        if estado_actual != "firmado":
            raise ValueError("Solo puede reabrirse un PIAR finalizado.")
        return "borrador"
