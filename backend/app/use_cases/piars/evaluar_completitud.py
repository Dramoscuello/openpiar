# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Reglas puras de completitud del formato PIAR MEN V15 08/2020."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


Registro = Mapping[str, Any]


@dataclass(frozen=True)
class PiarCompletitudData:
    general: Registro
    salud: Registro | None = None
    hogar: Registro | None = None
    trayectoria: Registro | None = None
    matricula: Registro | None = None
    caracteristicas: Registro | None = None
    participantes: Sequence[Registro] = field(default_factory=tuple)
    asignaturas: Sequence[Registro] = field(default_factory=tuple)
    ajustes: Sequence[Registro] = field(default_factory=tuple)
    acta: Registro | None = None
    compromisos_casa: Sequence[Registro] = field(default_factory=tuple)


@dataclass(frozen=True)
class SeccionCompletitud:
    codigo: str
    nombre: str
    faltantes: tuple[str, ...]

    @property
    def completa(self) -> bool:
        return not self.faltantes


@dataclass(frozen=True)
class ResultadoCompletitud:
    porcentaje: int
    secciones: tuple[SeccionCompletitud, ...]

    @property
    def completa(self) -> bool:
        return all(seccion.completa for seccion in self.secciones)


def _vacio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _requerir(registro: Registro, campos: Sequence[tuple[str, str]]) -> list[str]:
    return [etiqueta for campo, etiqueta in campos if _vacio(registro.get(campo))]


class EvaluarCompletitudPiarUseCase:
    """Evalúa el PIAR sin depender de HTTP, ORM o una base de datos."""

    def execute(self, data: PiarCompletitudData) -> ResultadoCompletitud:
        secciones = (
            self._general(data.general),
            self._salud(data.salud),
            self._hogar(data.hogar),
            self._trayectoria(data.trayectoria, data.matricula),
            self._caracterizacion(data.caracteristicas, data.participantes),
            self._ajustes(data.asignaturas, data.ajustes),
            self._acta(data.acta, data.compromisos_casa),
        )
        completas = sum(1 for seccion in secciones if seccion.completa)
        return ResultadoCompletitud(
            porcentaje=round(completas * 100 / len(secciones)),
            secciones=secciones,
        )

    def _general(self, general: Registro) -> SeccionCompletitud:
        faltantes = _requerir(general, (
            ("nombres", "Nombres"),
            ("apellidos", "Apellidos"),
            ("tipo_documento", "Tipo de identificación"),
            ("numero_documento", "Número de identificación"),
            ("fecha_nacimiento", "Fecha de nacimiento"),
            ("grupo_id", "Sede y grupo"),
            ("lugar_nacimiento", "Lugar de nacimiento"),
            ("departamento_residencia", "Departamento de residencia"),
            ("municipio_residencia", "Municipio de residencia"),
            ("direccion", "Dirección de vivienda"),
            ("barrio_vereda", "Barrio o vereda"),
            ("lugar_diligenciamiento", "Lugar de diligenciamiento"),
        ))
        for campo, etiqueta in (
            ("en_centro_proteccion", "Pertenencia a centro de protección"),
            ("pertenece_grupo_etnico", "Pertenencia a grupo étnico"),
            ("victima_conflicto", "Condición de víctima del conflicto"),
        ):
            if general.get(campo) is None:
                faltantes.append(etiqueta)
        if general.get("en_centro_proteccion") and _vacio(general.get("centro_proteccion_donde")):
            faltantes.append("Centro de protección")
        if general.get("pertenece_grupo_etnico") and _vacio(general.get("grupo_etnico")):
            faltantes.append("Grupo étnico")
        if general.get("victima_conflicto") and general.get("registro_victima") is None:
            faltantes.append("Registro como víctima")
        return SeccionCompletitud("general", "Información general", tuple(faltantes))

    def _salud(self, salud: Registro | None) -> SeccionCompletitud:
        if salud is None:
            return SeccionCompletitud("salud", "Entorno salud", ("Entorno de salud",))
        faltantes: list[str] = []
        if salud.get("afiliacion_salud"):
            faltantes += _requerir(salud, (("eps", "EPS"), ("regimen", "Régimen de salud")))
        if salud.get("tiene_diagnostico_medico") and _vacio(salud.get("diagnostico_medico")):
            faltantes.append("Diagnóstico médico")
        if salud.get("atendido_sector_salud") and not salud.get("atenciones_medicas"):
            faltantes.append("Atenciones médicas y frecuencia")
        if salud.get("asiste_terapias") and not salud.get("terapias_detalle"):
            faltantes.append("Intervenciones terapéuticas y frecuencia")
        if salud.get("consume_medicamentos") and not (
            salud.get("medicamentos_lista") or salud.get("medicamentos_detalle")
        ):
            faltantes.append("Medicamentos, frecuencia y horario")
        if salud.get("productos_apoyo_movilidad") and _vacio(salud.get("productos_apoyo_cual")):
            faltantes.append("Apoyos o ayudas técnicas")
        return SeccionCompletitud("salud", "Entorno salud", tuple(faltantes))

    def _hogar(self, hogar: Registro | None) -> SeccionCompletitud:
        if hogar is None:
            return SeccionCompletitud("hogar", "Entorno hogar", ("Entorno de hogar",))
        faltantes = _requerir(hogar, (
            ("acudiente_principal", "Acudiente principal"),
            ("personas_vive_estudiante", "Personas con quienes vive"),
            ("apoyo_crianza", "Personas que apoyan la crianza"),
        ))
        if not any(not _vacio(hogar.get(campo)) for campo in ("nombre_madre", "nombre_padre", "nombre_cuidador")):
            faltantes.append("Datos de madre, padre o cuidador")
        return SeccionCompletitud("hogar", "Entorno hogar", tuple(faltantes))

    def _trayectoria(self, trayectoria: Registro | None, matricula: Registro | None) -> SeccionCompletitud:
        if trayectoria is None:
            return SeccionCompletitud("trayectoria", "Entorno educativo", ("Trayectoria educativa",))
        faltantes = _requerir(trayectoria, (
            ("ultimo_grado_cursado", "Último grado cursado"),
            ("estado_ultimo_grado", "Estado del último grado"),
        ))
        if trayectoria.get("vinculado_sistema_anterior") is None:
            faltantes.append("Vinculación al sistema educativo el año anterior")
        if trayectoria.get("vinculado_educacion_inicial") and _vacio(
            trayectoria.get("educacion_inicial_instituciones")
        ):
            faltantes.append("Instituciones educativas anteriores")
        if trayectoria.get("recibe_informe_pedagogico") and _vacio(
            trayectoria.get("institucion_procedencia_informe")
        ):
            faltantes.append("Procedencia del informe pedagógico")
        if trayectoria.get("asiste_programas_complementarios") and _vacio(
            trayectoria.get("programas_complementarios_cuales")
        ):
            faltantes.append("Programas complementarios")
        if matricula is None:
            faltantes.append("Matrícula actual")
        return SeccionCompletitud("trayectoria", "Entorno educativo", tuple(faltantes))

    def _caracterizacion(
        self, caracteristicas: Registro | None, participantes: Sequence[Registro]
    ) -> SeccionCompletitud:
        if caracteristicas is None:
            return SeccionCompletitud(
                "caracterizacion", "Caracterización y participantes", ("Caracterización del estudiante",)
            )
        faltantes = _requerir(caracteristicas, (
            ("descripcion_habilidades", "Capacidades y habilidades"),
            ("descripcion_gustos_intereses", "Gustos e intereses"),
            ("expectativas_estudiante", "Expectativas del estudiante"),
            ("expectativas_familia", "Expectativas de la familia"),
            ("redes_apoyo", "Redes de apoyo"),
            ("entorno_familiar_social_economico", "Entorno familiar, social y económico"),
            ("caracterizacion_pedagogica", "Caracterización pedagógica"),
        ))
        if not any(participante.get("confirmado") for participante in participantes):
            faltantes.append("Participantes que elaboran el PIAR")
        return SeccionCompletitud(
            "caracterizacion", "Caracterización y participantes", tuple(faltantes)
        )

    def _ajustes(
        self, asignaturas: Sequence[Registro], ajustes: Sequence[Registro]
    ) -> SeccionCompletitud:
        faltantes: list[str] = []
        if not asignaturas:
            faltantes.append("Carga académica del grupo")
        for asignatura in asignaturas:
            estado = asignatura.get("estado")
            nombre = asignatura.get("nombre_asignatura") or "Asignatura"
            if estado == "pendiente":
                faltantes.append(f"Resolver {nombre}")
            elif estado == "no_requiere" and _vacio(asignatura.get("justificacion")):
                faltantes.append(f"Justificación de {nombre}")
        campos_ajuste = (
            "objetivos_propositos", "barreras_evidenciadas", "tipo_ajuste",
            "apoyo_requerido", "ajustes_estrategias",
        )
        for ajuste in ajustes:
            if any(_vacio(ajuste.get(campo)) for campo in campos_ajuste):
                faltantes.append(f"Completar ajuste de {ajuste.get('area') or 'asignatura'}")
        return SeccionCompletitud("ajustes", "Matriz de ajustes razonables", tuple(faltantes))

    def _acta(
        self, acta: Registro | None, compromisos: Sequence[Registro]
    ) -> SeccionCompletitud:
        if acta is None:
            return SeccionCompletitud("acta", "Acta de acuerdo", ("Acta de acuerdo",))
        faltantes = _requerir(acta, (("compromisos_aula", "Compromisos de aula"),))
        if not compromisos:
            faltantes.append("Al menos una actividad de apoyo en casa")
        for campo, etiqueta in (
            ("firmado_estudiante", "Confirmación de firma del estudiante"),
            ("firmado_acudiente", "Confirmación de firma del acudiente"),
            ("firmado_docentes_aula", "Confirmación de firma de docentes"),
            ("firmado_directivo", "Confirmación de firma del directivo"),
        ):
            if not acta.get(campo):
                faltantes.append(etiqueta)
        return SeccionCompletitud("acta", "Acta de acuerdo", tuple(faltantes))
