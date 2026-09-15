# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Construcción pura de los metadatos verificables de una versión PIAR."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class VersionPiarData:
    numero: int
    snapshot: Mapping[str, Any]
    pdf: bytes
    sha256: str


class VersionarPiarUseCase:
    def execute(self, numero: int, snapshot: Mapping[str, Any], pdf: bytes) -> VersionPiarData:
        if numero < 1:
            raise ValueError("El número de versión debe ser positivo.")
        if not pdf.startswith(b"%PDF"):
            raise ValueError("El archivo final no contiene un PDF válido.")
        return VersionPiarData(
            numero=numero,
            snapshot=snapshot,
            pdf=pdf,
            sha256=hashlib.sha256(pdf).hexdigest(),
        )
