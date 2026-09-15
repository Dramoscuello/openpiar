# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Prueba de humo y extracción del PDF oficial PIAR."""

from datetime import date
from io import BytesIO
from types import SimpleNamespace as NS

from pypdf import PdfReader

from app.core.pdf_generator import generate_piar_oficial_pdf


def ns(**kwargs):
    return NS(**kwargs)


def crear_piar_pdf_texto_extenso():
    salud = ns(
        afiliacion_salud=True, eps="EPS Salud & Vida", regimen="contributivo",
        lugar_emergencias="Clínica <Central>", atendido_sector_salud=True,
        tiene_diagnostico_medico=True, diagnostico_medico="Diagnóstico & seguimiento",
        asiste_terapias=True, consume_medicamentos=True,
        productos_apoyo_movilidad=True, productos_apoyo_cual="Audífonos",
        atenciones_medicas=[{"cual": "Neurología", "frecuencia": "semestral"}],
        terapias_detalle=[{"tipo": "Lenguaje", "frecuencia": "semanal"}],
        medicamentos_lista=[{"cual": "Medicamento A", "frecuencia": "diaria"}],
    )
    hogar = ns(
        nombre_madre="Ana", nombre_padre="Luis", ocupacion_madre="Comerciante",
        ocupacion_padre="Técnico", nivel_educativo_madre="Bachiller",
        nivel_educativo_padre="Técnico", nombre_cuidador="Ana",
        nivel_educativo_cuidador="Bachiller", parentesco_cuidador="Madre",
        telefono_cuidador="3000000000", correo_cuidador="ana@example.com",
        personas_vive_estudiante="Madre y hermano", numero_hermanos=1,
        lugar_que_ocupa=1, apoyo_crianza="Familia extensa",
    )
    trayectoria = ns(
        vinculado_sistema_anterior=True, vinculado_educacion_inicial=True,
        educacion_inicial_instituciones="IE anterior", ultimo_grado_cursado="Quinto",
        estado_ultimo_grado="aprobado", observaciones_trayectoria="Continuidad regular",
        recibe_informe_pedagogico=True, institucion_procedencia_informe="IE anterior",
        asiste_programas_complementarios=True,
        programas_complementarios_cuales="Música",
    )
    estudiante = ns(
        nombres="María & Luz", apellidos="Pérez <Gómez>", tipo_documento="TI",
        numero_documento="123456", fecha_nacimiento=date(2014, 5, 20),
        lugar_nacimiento="Bogotá", departamento_residencia="Cundinamarca",
        municipio_residencia="Bogotá", direccion="Calle 1 & 2", barrio_vereda="Centro",
        telefono="", correo="", victima_conflicto=False, registro_victima=None,
        en_centro_proteccion=False, centro_proteccion_donde=None,
        pertenece_grupo_etnico=False, grupo_etnico=None,
        grupo=ns(grado=ns(nombre="Sexto"), sede=ns(nombre="Principal")),
        entorno_salud=salud, entorno_hogar=hogar,
        trayectoria_educativa=trayectoria,
        matricula_actual=ns(),
    )
    caracteristicas = ns(
        descripcion_gustos_intereses="Arte & música", descripcion_habilidades="Memoria visual",
        expectativas_estudiante="Aprender", expectativas_familia="Avanzar",
        redes_apoyo="Familia", entorno_familiar_social_economico="Entorno estable",
        otras_observaciones="Texto con <etiquetas> que debe mostrarse como contenido.",
        caracterizacion_pedagogica="Caracterización extensa. " * 120,
    )
    ajuste = ns(
        area="Matemáticas", titulo_tema="Fracciones", objetivos_propositos="Resolver problemas",
        dba_referencia="DBA 1", barreras_evidenciadas="Barrera comunicativa. " * 90,
        tipo_ajuste="Didácticas", apoyo_requerido="Talento humano: docente.",
        ajustes_estrategias="Presentar información visual. " * 120,
        evaluacion_ajustes="Rúbrica", temporalidad="Semanal", responsable="Docente",
        medios_verificacion="Portafolio",
    )
    acta = ns(
        fecha_firma=date(2026, 9, 8), compromisos_aula="Aplicar los apoyos acordados.",
        compromisos_casa=[ns(nombre_actividad="Lectura", descripcion_estrategia="Leer en familia", frecuencia="diaria")],
        firmado_estudiante=True, firmado_acudiente=True, firmado_docentes_aula=True,
        firmado_directivo=True,
    )
    return ns(
        estudiante=estudiante, fecha_creacion=date(2026, 9, 8),
        lugar_diligenciamiento="Bogotá D.C.", docentes_elaboran="Docente Uno",
        participantes=[ns(nombre="Docente Uno", area="Matemáticas", rol_piar="docente_aula")],
        caracteristicas=caracteristicas, ajustes_razonables=[ajuste],
        asignaturas_estado=[], acta_acuerdo=acta,
    )


def test_pdf_borrador_escapa_texto_y_no_crea_paginas_vacias():
    piar = crear_piar_pdf_texto_extenso()
    config = ns(nombre_institucion="Institución Educativa & Comunidad")
    pdf = generate_piar_oficial_pdf(
        piar, config, [], modo="borrador", faltantes=["Salud: dato <pendiente>"]
    )

    assert pdf.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf))
    textos = [(pagina.extract_text() or "").strip() for pagina in reader.pages]
    assert len(textos) >= 6
    assert all(textos)
    contenido = "\n".join(textos)
    assert "BORRADOR" in contenido
    assert "María & Luz" in contenido
    assert "V15. 08/2020" in contenido


def test_pdf_final_conserva_espacios_de_firma_sin_marca_de_agua():
    pdf = generate_piar_oficial_pdf(
        crear_piar_pdf_texto_extenso(),
        ns(nombre_institucion="Institución Educativa"),
        [],
        modo="final",
    )
    contenido = "\n".join(
        pagina.extract_text() or "" for pagina in PdfReader(BytesIO(pdf)).pages
    )
    assert "BORRADOR" not in contenido
    assert "Firmado electrónicamente" not in contenido
    assert "Firma de los Actores comprometidos" in contenido


def test_justificacion_sin_ajuste_aparece_en_matriz_horizontal():
    piar = crear_piar_pdf_texto_extenso()
    piar.asignaturas_estado = [ns(
        estado="no_requiere", nombre_asignatura="Educación artística",
        justificacion="Participa en arte & música <sin apoyo adicional>.",
    )]
    pdf = generate_piar_oficial_pdf(piar, ns(nombre_institucion="IE de prueba"), [], modo="borrador")
    reader = PdfReader(BytesIO(pdf))
    pagina = next(p for p in reader.pages if "Participa en arte" in (p.extract_text() or ""))
    texto = pagina.extract_text()
    assert pagina.mediabox.width > pagina.mediabox.height
    assert "Educación artística" in texto
    assert "No requiere ajuste razonable" in texto
    assert "Descripción de tipo de ajustes y apoyos" in texto
    assert "Participa en arte & música <sin apoyo adicional>." in texto
