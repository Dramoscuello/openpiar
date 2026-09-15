# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Pruebas de completitud, condicionales y versionado inmutable del PIAR."""

from copy import deepcopy

import pytest

from app.use_cases.piars import (
    EvaluarCompletitudPiarUseCase,
    FinalizarPiarUseCase,
    PiarCompletitudData,
    PiarIncompletoError,
    ReabrirPiarUseCase,
    VersionarPiarUseCase,
)


def datos_completos() -> PiarCompletitudData:
    return PiarCompletitudData(
        general={
            "nombres": "María", "apellidos": "López", "tipo_documento": "TI",
            "numero_documento": "12345", "fecha_nacimiento": "2014-05-01",
            "grupo_id": "grupo", "lugar_nacimiento": "Cali",
            "departamento_residencia": "Valle", "municipio_residencia": "Cali",
            "direccion": "Calle 1 & 2", "barrio_vereda": "Centro",
            "en_centro_proteccion": False, "pertenece_grupo_etnico": False,
            "victima_conflicto": False,
            "lugar_diligenciamiento": "Cali",
        },
        salud={"afiliacion_salud": False, "tiene_diagnostico_medico": False},
        hogar={
            "nombre_madre": "Ana", "acudiente_principal": "madre",
            "personas_vive_estudiante": "Madre", "apoyo_crianza": "Abuela",
        },
        trayectoria={
            "vinculado_sistema_anterior": True,
            "vinculado_educacion_inicial": False,
            "ultimo_grado_cursado": "Quinto", "estado_ultimo_grado": "aprobado",
            "recibe_informe_pedagogico": False,
            "asiste_programas_complementarios": False,
        },
        matricula={"institucion_educativa": "IE", "sede": "Principal", "grado_ingreso": "Sexto", "jornada": "unica"},
        caracteristicas={
            "descripcion_habilidades": "Memoria visual", "descripcion_gustos_intereses": "Arte",
            "expectativas_estudiante": "Aprender", "expectativas_familia": "Avanzar",
            "redes_apoyo": "Familia", "entorno_familiar_social_economico": "Estable",
            "caracterizacion_pedagogica": "Aprende mejor con apoyos visuales",
        },
        participantes=[{"nombre": "Docente", "confirmado": True}],
        asignaturas=[{"asignatura_id": "mat", "nombre_asignatura": "Matemáticas", "estado": "no_requiere", "justificacion": "Alcanza las metas sin ajuste."}],
        ajustes=[],
        acta={
            "compromisos_aula": "Aplicar DUA", "firmado_estudiante": True,
            "firmado_acudiente": True, "firmado_docentes_aula": True,
            "firmado_directivo": True,
        },
        compromisos_casa=[{"nombre_actividad": "Lectura", "descripcion_estrategia": "Leer juntos", "frecuencia": "diaria"}],
    )


def test_piar_completo_autoriza_version_final():
    resultado = EvaluarCompletitudPiarUseCase().execute(datos_completos())
    assert resultado.completa
    assert resultado.porcentaje == 100
    assert FinalizarPiarUseCase().execute(resultado, 2) == 3


@pytest.mark.parametrize("valor_opcional", [None, ""])
def test_finaliza_con_ajuste_sin_seguimiento_ni_referencia_curricular(valor_opcional):
    datos = datos_completos()
    ajuste = {
        "asignatura_id": "mat", "area": "Matemáticas",
        "objetivos_propositos": "Resolver sumas", "barreras_evidenciadas": "Texto denso",
        "tipo_ajuste": "Didáctico", "apoyo_requerido": "Material visual",
        "ajustes_estrategias": "Representar las cantidades con objetos",
        **{campo: valor_opcional for campo in (
            "temporalidad", "responsable", "medios_verificacion",
            "evaluacion_ajustes", "dba_referencia", "ebc_referencia",
        )},
    }
    resultado = EvaluarCompletitudPiarUseCase().execute(PiarCompletitudData(**{
        **datos.__dict__, "ajustes": [ajuste],
        "asignaturas": [dict(datos.asignaturas[0], estado="con_ajuste", justificacion=None)],
    }))
    assert resultado.completa
    assert resultado.porcentaje == 100
    assert FinalizarPiarUseCase().execute(resultado, 0) == 1


@pytest.mark.parametrize("campo", [
    "objetivos_propositos", "barreras_evidenciadas", "tipo_ajuste",
    "apoyo_requerido", "ajustes_estrategias",
])
def test_los_campos_principales_del_ajuste_siguen_siendo_obligatorios(campo):
    datos = datos_completos()
    ajuste = dict.fromkeys([
        "objetivos_propositos", "barreras_evidenciadas", "tipo_ajuste",
        "apoyo_requerido", "ajustes_estrategias",
    ], "Información diligenciada")
    ajuste.update(area="Matemáticas", asignatura_id="mat")
    ajuste[campo] = ""
    resultado = EvaluarCompletitudPiarUseCase().execute(PiarCompletitudData(**{
        **datos.__dict__, "ajustes": [ajuste],
        "asignaturas": [dict(datos.asignaturas[0], estado="con_ajuste", justificacion=None)],
    }))
    assert not resultado.completa
    with pytest.raises(PiarIncompletoError):
        FinalizarPiarUseCase().execute(resultado, 0)


def test_asignatura_no_requiere_exige_justificacion():
    datos = datos_completos()
    asignaturas = [dict(datos.asignaturas[0], justificacion="")]
    resultado = EvaluarCompletitudPiarUseCase().execute(
        PiarCompletitudData(**{**datos.__dict__, "asignaturas": asignaturas})
    )
    assert not resultado.completa
    assert "Justificación de Matemáticas" in next(s for s in resultado.secciones if s.codigo == "ajustes").faltantes
    with pytest.raises(PiarIncompletoError):
        FinalizarPiarUseCase().execute(resultado, 0)


def test_validacion_condicional_y_hash_pdf_inmutable():
    datos = datos_completos()
    general = deepcopy(dict(datos.general))
    general.update(en_centro_proteccion=True, centro_proteccion_donde="")
    resultado = EvaluarCompletitudPiarUseCase().execute(
        PiarCompletitudData(**{**datos.__dict__, "general": general})
    )
    assert "Centro de protección" in resultado.secciones[0].faltantes

    pdf = b"%PDF-1.4\ncontenido & <acentos>"
    version = VersionarPiarUseCase().execute(1, {"nombre": "María"}, pdf)
    assert version.pdf == pdf
    assert len(version.sha256) == 64
    assert ReabrirPiarUseCase().execute("firmado") == "borrador"
