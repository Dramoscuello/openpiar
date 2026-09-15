# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Prueba de humo y extracción del PDF oficial PIAR."""

from datetime import date
from io import BytesIO
from types import SimpleNamespace as NS

import fitz
import pdfplumber
import pytest
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
        periodo_id=1,
        area="Matemáticas", titulo_tema="Fracciones", objetivos_propositos="Resolver problemas",
        dba_referencia="DBA 1", barreras_evidenciadas="Barrera comunicativa. " * 90,
        tipo_ajuste="Didácticas", apoyo_requerido="Talento humano: docente.",
        ajustes_estrategias="Presentar información visual. " * 120,
        evaluacion_ajustes="Rúbrica", temporalidad="Semanal", responsable="Docente",
        medios_verificacion="Portafolio",
    )
    acta = ns(
        periodo_id=1,
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
        asignaturas_estado=[], actas_acuerdo=[acta],
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


@pytest.mark.parametrize("modo", ["borrador", "final"])
def test_primera_pagina_identifica_solo_al_director_actual_y_direccion_institucional(modo):
    piar = crear_piar_pdf_texto_extenso()
    piar.estudiante.grupo.director = ns(nombre="Clara & Luz", apellido="Gómez")
    # Ni el primer participante ni un director anterior deben reemplazar al actual.
    piar.participantes.append(ns(nombre="Director Anterior", area=None, rol_piar="director_grupo"))
    pdf = generate_piar_oficial_pdf(
        piar, ns(nombre_institucion="IE", direccion="Carrera 12 # 34-56 <Principal>"), [], modo=modo,
    )
    reader = PdfReader(BytesIO(pdf))
    texto = reader.pages[0].extract_text()
    assert "Clara & Luz Gómez (Docente director de grupo)" in texto
    assert "Docente Uno" not in texto
    assert "Director Anterior" not in texto
    assert "08/09/2026 Carrera 12 # 34-56 <Principal>" in texto
    assert "Bogotá D.C." not in texto
    # El encabezado repetido del acta también usa la dirección institucional.
    assert "Carrera 12 # 34-56 <Principal>" in reader.pages[-1].extract_text()


@pytest.mark.parametrize("sin_grupo", [False, True])
def test_sin_director_no_atribuye_diligenciamiento_a_otro_participante(sin_grupo):
    piar = crear_piar_pdf_texto_extenso()
    if sin_grupo:
        piar.estudiante.grupo = None
    else:
        piar.estudiante.grupo.director = None
    pdf = generate_piar_oficial_pdf(piar, None, [])
    texto = PdfReader(BytesIO(pdf)).pages[0].extract_text()
    assert "Director de grupo no asignado" in texto
    assert "Docente Uno" not in texto
    assert "Bogotá D.C." not in texto


def _tablas_pdf(pagina):
    # Ignorar bordes de rectángulos de fondo: solo las líneas de la cuadrícula
    # delimitan las celdas visibles, incluidas las combinadas.
    return pagina.find_tables({
        "vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict",
    })


def _texto_celda(valor):
    return " ".join((valor or "").split())


def test_etiquetas_generales_ocupan_el_ancho_hasta_su_valor_sin_celdas_vacias():
    piar = crear_piar_pdf_texto_extenso()
    piar.estudiante.correo = "correo@example.com"
    piar.estudiante.pertenece_grupo_etnico = True
    piar.estudiante.grupo_etnico = "Pueblo de prueba"
    pdf = generate_piar_oficial_pdf(piar, None, [])
    esperados = {
        "Barrio/vereda": "Centro",
        "Correo electrónico": "correo@example.com",
        "¿Se reconoce o pertenece a un grupo étnico?": "Si _x_ No ___ ¿Cuál? Pueblo de prueba",
    }
    with pdfplumber.open(BytesIO(pdf)) as documento:
        filas = [fila for tabla in _tablas_pdf(documento.pages[0]) for fila in tabla.extract()]
    for etiqueta, valor in esperados.items():
        fila = next(f for f in filas if etiqueta in [_texto_celda(c) for c in f])
        celdas = [_texto_celda(c) for c in fila]
        assert celdas[celdas.index(etiqueta) + 1] == valor


def test_eps_y_detalles_de_salud_tienen_etiquetas_y_valores_en_celdas_distintas():
    pdf = generate_piar_oficial_pdf(crear_piar_pdf_texto_extenso(), None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        filas = [
            [_texto_celda(c) for c in fila if c is not None]
            for pagina in documento.pages for tabla in _tablas_pdf(pagina) for fila in tabla.extract()
        ]
    for valor in ["EPS Salud & Vida", "Diagnóstico & seguimiento", "Neurología", "Lenguaje", "Medicamento A", "Audífonos"]:
        fila = next(f for f in filas if valor in f)
        assert fila[fila.index(valor) - 1] in ("¿Cuál?", "¿Cuáles?")


@pytest.mark.parametrize("asiste", [True, False, None, "sin_trayectoria"])
def test_entorno_educativo_muestra_procedencia_y_respuesta_de_programas(asiste):
    piar = crear_piar_pdf_texto_extenso()
    if asiste == "sin_trayectoria":
        piar.estudiante.trayectoria_educativa = None
    else:
        trayectoria = piar.estudiante.trayectoria_educativa
        trayectoria.institucion_procedencia_informe = "Escuela Origen & Comunidad"
        trayectoria.asiste_programas_complementarios = asiste
        trayectoria.programas_complementarios_cuales = "Música & natación"
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        filas = [
            [_texto_celda(c) for c in fila if c is not None]
            for pagina in documento.pages for tabla in _tablas_pdf(pagina) for fila in tabla.extract()
        ]
    informe = next(f for f in filas if f[0] == "¿De qué institución o modalidad proviene el informe?")
    assert informe[1] == ("" if asiste == "sin_trayectoria" else "Escuela Origen & Comunidad")
    programas = next(f for f in filas if f[0] == "¿Está asistiendo en la actualidad a programas complementarios?")
    assert programas[1] == (
        "SI [X] NO [ ] ¿Cuáles? Música & natación" if asiste is True else "SI [ ] NO [X]"
    )


@pytest.mark.parametrize("extenso", [False, True])
def test_firmas_fisicas_forman_tabla_2x2_inmediatamente_despues_del_entorno_educativo(extenso):
    piar = crear_piar_pdf_texto_extenso()
    if extenso:
        piar.estudiante.trayectoria_educativa.institucion_procedencia_informe = "Institución de procedencia. " * 30
        piar.estudiante.trayectoria_educativa.programas_complementarios_cuales = "Programa artístico y deportivo. " * 30
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(p for p in documento.pages if "Nombre y firma de quien diligencia" in p.extract_text())
        tablas = _tablas_pdf(pagina)
        firmas = next(t for t in tablas if t.extract()[0][0] == "Nombre y firma de quien diligencia")
        assert firmas.extract() == [
            ["Nombre y firma de quien diligencia", "Nombre y firma acudiente"], ["", ""],
        ]
        educativo = next(t for t in tablas if "programas complementarios" in _texto_celda(t.extract()[-1][0]))
        assert firmas.bbox[1] - educativo.bbox[3] == pytest.approx(8, abs=0.1)
        assert firmas.rows[1].bbox[3] - firmas.rows[1].bbox[1] >= 56  # 2 cm para firmar.


def test_anexo2_agrupa_docentes_por_nombre_con_cargos_y_areas_sin_repetir():
    piar = crear_piar_pdf_texto_extenso()
    piar.participantes = [
        ns(nombre="Clara & Luz", cargo="Docente", area="Matemáticas", rol_piar="docente_aula"),
        ns(nombre="Clara & Luz", cargo="Docente", area="Ciencias naturales", rol_piar="docente_aula"),
        ns(nombre="  clara  & luz ", cargo="docente", area=" matemáticas ", rol_piar="docente_aula"),
        ns(nombre="Clara & Luz", cargo=None, area=None, rol_piar="director_grupo"),
        ns(nombre="Pedro Gómez", cargo=None, area="Lenguaje", rol_piar="docente_aula"),
    ]
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(p for p in documento.pages if "ANEXO 2" in p.extract_text())
        fila = next(
            fila for tabla in _tablas_pdf(pagina) for fila in tabla.extract()
            if _texto_celda(fila[0]) == "Docentes que elaboran y cargo"
        )
        docentes = _texto_celda(fila[1])
    assert docentes == (
        "Clara & Luz - Docente, director grupo - Matemáticas, Ciencias naturales "
        "Pedro Gómez - docente aula - Lenguaje"
    )


def test_anexo2_conserva_docentes_elaboran_si_no_hay_participantes():
    piar = crear_piar_pdf_texto_extenso()
    piar.participantes = []
    piar.docentes_elaboran = "Docente histórico - Matemáticas y Ciencias"
    pdf = generate_piar_oficial_pdf(piar, None, [])
    pagina = next(p for p in PdfReader(BytesIO(pdf)).pages if "ANEXO 2" in p.extract_text())
    assert piar.docentes_elaboran in pagina.extract_text()


def test_caracterizacion_en_celda_conserva_todo_el_texto_al_dividirse_entre_paginas():
    piar = crear_piar_pdf_texto_extenso()
    frase = "Caracterización extensa con apoyos visuales."
    piar.caracteristicas.caracterizacion_pedagogica = (frase + " ") * 400
    pdf = generate_piar_oficial_pdf(piar, None, [])
    paginas = PdfReader(BytesIO(pdf)).pages
    texto = _texto_celda(" ".join(p.extract_text() for p in paginas))
    assert texto.count(frase) == 400
    assert sum("Caracterización extensa" in p.extract_text() for p in paginas) > 1
    assert "Firma de los Actores comprometidos" in texto


@pytest.mark.parametrize("cantidad_docentes", [2, 11])
def test_tabla_firmas_incluye_cada_docente_una_vez_con_todas_sus_areas(cantidad_docentes):
    piar = crear_piar_pdf_texto_extenso()
    piar.participantes = [
        ns(nombre=f"Docente {numero:02}", area=area, rol_piar="docente_aula")
        for numero in range(cantidad_docentes)
        for area in ("Matemáticas", "Ciencias naturales", " matemáticas ")
    ]
    piar.participantes.append(ns(nombre="  docente 00  ", area="Lenguaje", rol_piar="docente_aula"))
    pdf = generate_piar_oficial_pdf(piar, None, [])
    firmas = []
    with pdfplumber.open(BytesIO(pdf)) as documento:
        for pagina in documento.pages:
            for tabla in _tablas_pdf(pagina):
                filas = tabla.extract()
                if filas[0] == ["Nombre docente"] * 3:
                    assert len(filas) == 6
                    assert filas[2] == ["Área"] * 3
                    assert filas[4] == ["Firma"] * 3
                    for nombre, area in zip(filas[1], filas[3]):
                        if nombre:
                            firmas.append((_texto_celda(nombre), _texto_celda(area)))
    assert firmas == [
        (f"Docente {numero:02}", "Matemáticas, Ciencias naturales" + (", Lenguaje" if numero == 0 else ""))
        for numero in range(cantidad_docentes)
    ]


def test_matriz_separa_asignatura_tema_y_propositos_con_saltos_de_linea():
    pdf = generate_piar_oficial_pdf(crear_piar_pdf_texto_extenso(), None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(
            p for p in documento.pages if "Área/asignatura" in (p.extract_text() or "")
        )
        # La fila puede dividirse entre páginas; se reconstruyen las líneas de la
        # primera columna por posición para verificar los saltos de línea.
        verticales = sorted({
            round(linea["x0"], 1)
            for linea in pagina.lines
            if abs(linea["x0"] - linea["x1"]) < 1
        })
        limite = verticales[1] if len(verticales) > 1 else 145
        lineas: list[tuple[float, list[str]]] = []
        for palabra in pagina.extract_words():
            if palabra["x0"] >= limite - 1:
                continue
            if not lineas or abs(palabra["top"] - lineas[-1][0]) > 3:
                lineas.append((palabra["top"], [palabra["text"]]))
            else:
                lineas[-1][1].append(palabra["text"])
        textos = [" ".join(partes) for _, partes in lineas]

    assert "1. Matemáticas" in textos
    assert "Fracciones" in textos
    assert any(texto.startswith("Objetivos / Propósitos") for texto in textos)
    assert "DBA: DBA 1" in textos


@pytest.mark.parametrize("con_compromisos", [False, True])
def test_acta_muestra_textos_en_celdas_y_compromisos_bajo_el_instructivo(con_compromisos):
    piar = crear_piar_pdf_texto_extenso()
    if not con_compromisos:
        piar.actas_acuerdo[0].compromisos_aula = None
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(
            p for p in documento.pages if "ACTA DE ACUERDO" in (p.extract_text() or "")
        )
        contenido = pagina.extract_text() or ""

        for texto in ("Según el Decreto 1421", "Y en casa apoyará con las siguientes actividades:"):
            caja = pagina.search(texto)[0]
            lineas = [
                linea for linea in pagina.lines
                if abs(linea["top"] - linea["bottom"]) < 1
                and linea["x0"] <= caja["x0"] + 2
                and linea["x1"] >= caja["x1"] - 2
            ]
            assert any(linea["top"] < caja["top"] for linea in lineas)
            assert any(linea["bottom"] > caja["bottom"] for linea in lineas)

    instructivo = "Incluya aquí los compromisos específicos para implementar en el aula"
    assert instructivo in contenido
    if con_compromisos:
        assert "Aplicar los apoyos acordados." in contenido
        assert contenido.index(instructivo) < contenido.index("Aplicar los apoyos acordados.")


def test_celdas_de_firma_docente_tienen_altura_fija_para_firma_fisica():
    pdf = generate_piar_oficial_pdf(crear_piar_pdf_texto_extenso(), None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        tablas = [tabla for pagina in documento.pages for tabla in _tablas_pdf(pagina)]
    docente = next(t for t in tablas if t.extract()[0] == ["Nombre docente"] * 3)
    apoyo = next(t for t in tablas if t.extract()[0][0] == "Nombre docente orientador")
    for tabla in (docente, apoyo):
        altura_firma = tabla.rows[5].bbox[3] - tabla.rows[5].bbox[1]
        assert altura_firma >= 56  # 2 cm de espacio para la firma física.


def test_fechas_del_pdf_toman_la_fecha_de_firma_del_acta():
    piar = crear_piar_pdf_texto_extenso()
    piar.fecha_creacion = date(2026, 1, 15)
    piar.actas_acuerdo[0].fecha_firma = date(2026, 9, 8)
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        paginas = [p.extract_text() or "" for p in documento.pages]

    primera = paginas[0]
    assert "08/09/2026" in primera
    assert "15/01/2026" not in primera
    anexo2 = next(texto for texto in paginas if "ANEXO 2" in texto)
    assert "08/09/2026" in anexo2
    assert "15/01/2026" not in anexo2
    acta = next(texto for texto in paginas if "ACTA DE ACUERDO" in texto)
    assert "08/09/2026" in acta


def test_acta_sin_fecha_de_firma_muestra_patron_ddmmaaaa_en_todas_las_secciones():
    piar = crear_piar_pdf_texto_extenso()
    piar.actas_acuerdo[0].fecha_firma = None
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        paginas = [p.extract_text() or "" for p in documento.pages]

    assert "DD/MM/AAAA" in paginas[0]
    anexo2 = next(texto for texto in paginas if "ANEXO 2" in texto)
    assert "DD/MM/AAAA" in anexo2
    acta = next(texto for texto in paginas if "ACTA DE ACUERDO" in texto)
    assert "DD/MM/AAAA" in acta


@pytest.mark.parametrize("cantidad", [0, 1, 3])
def test_tabla_casa_no_incluye_filas_vacias(cantidad):
    piar = crear_piar_pdf_texto_extenso()
    piar.actas_acuerdo[0].compromisos_casa = [
        ns(
            nombre_actividad=f"Actividad {indice}",
            descripcion_estrategia=f"Estrategia {indice}",
            frecuencia="diaria",
        )
        for indice in range(cantidad)
    ]
    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(
            p for p in documento.pages if "ACTA DE ACUERDO" in (p.extract_text() or "")
        )
        tabla = next(
            t for t in _tablas_pdf(pagina)
            if _texto_celda(t.extract()[0][0]) == "Nombre de la Actividad"
        )
    assert len(tabla.extract()) == cantidad + 1


def test_firmas_marcan_area_y_firma_con_el_estilo_de_titular():
    pdf = generate_piar_oficial_pdf(crear_piar_pdf_texto_extenso(), None, [])
    documento = fitz.open(stream=pdf, filetype="pdf")
    pagina = next(p for p in documento if "Nombre docente" in p.get_text())
    fondos = pagina.get_drawings()

    def tiene_fondo_gris(rect) -> bool:
        x = (rect.x0 + rect.x1) / 2
        y = (rect.y0 + rect.y1) / 2
        for dibujo in fondos:
            relleno = dibujo.get("fill")
            if not relleno or len(relleno) < 3 or not all(abs(c - 0.851) < 0.02 for c in relleno[:3]):
                continue
            for item in dibujo["items"]:
                if item[0] == "re" and item[1].x0 <= x <= item[1].x1 and item[1].y0 <= y <= item[1].y1:
                    return True
        return False

    for etiqueta in ("Nombre docente", "Área", "Firma"):
        coincidencias = pagina.search_for(etiqueta)
        assert coincidencias
        assert all(tiene_fondo_gris(rect) for rect in coincidencias)


def test_descripcion_de_ajustes_ocupa_una_sola_celda():
    piar = crear_piar_pdf_texto_extenso()
    piar.ajustes_razonables[0].barreras_evidenciadas = "Barrera comunicativa."
    piar.ajustes_razonables[0].ajustes_estrategias = "Estrategia de apoyo concreta. " * 60

    pdf = generate_piar_oficial_pdf(piar, None, [])
    with pdfplumber.open(BytesIO(pdf)) as documento:
        pagina = next(
            p for p in documento.pages if "Área/asignatura" in (p.extract_text() or "")
        )
        tabla = next(
            t for t in _tablas_pdf(pagina)
            if _texto_celda(t.extract()[0][0]).startswith("Área/asignatura")
        )
        cx0, ctop, cx1, cbottom = tabla.rows[2].cells[4]  # celda de la descripción
        lineas_internas = [
            linea for linea in pagina.lines
            if abs(linea["top"] - linea["bottom"]) < 1
            and linea["x0"] <= cx0 + 1 and linea["x1"] >= cx1 - 1
            and ctop + 2 < linea["top"] < cbottom - 2
        ]

    assert lineas_internas == []
    contenido = _texto_celda(tabla.extract()[2][4])
    assert contenido.count("Estrategia") == 60


def test_pdf_por_periodo_solo_incluye_ajustes_del_periodo():
    piar = crear_piar_pdf_texto_extenso()
    piar.ajustes_razonables.append(ns(
        periodo_id=2, area="Ciencias naturales", titulo_tema="Ecosistemas",
        objetivos_propositos="Identificar ecosistemas", barreras_evidenciadas="Vocabulario técnico",
        tipo_ajuste="Didácticas", apoyo_requerido="Material concreto",
        ajustes_estrategias="Usar mapas mentales", evaluacion_ajustes=None,
        temporalidad=None, responsable=None, medios_verificacion=None, dba_referencia=None,
    ))

    pdf = generate_piar_oficial_pdf(piar, None, [], periodo=NS(id=1))
    contenido = " ".join(
        (p.extract_text() or "") for p in PdfReader(BytesIO(pdf)).pages
    )
    contenido = " ".join(contenido.split())
    assert "Resolver problemas" in contenido
    assert "Ecosistemas" not in contenido

    pdf_p2 = generate_piar_oficial_pdf(piar, None, [], periodo=NS(id=2))
    contenido_p2 = " ".join(
        (p.extract_text() or "") for p in PdfReader(BytesIO(pdf_p2)).pages
    )
    contenido_p2 = " ".join(contenido_p2.split())
    assert "Ecosistemas" in contenido_p2
    assert "Resolver problemas" not in contenido_p2


def _evidencia_ns(ruta, **kwargs):
    base = dict(
        nombre_archivo="trabajo.jpg", tipo_archivo="imagen", ruta_archivo=str(ruta),
        descripcion="Trabajo en clase", fecha=date(2026, 9, 10), fecha_subida=None,
        creador=ns(nombre="Clara", apellido="Gómez"),
    )
    base.update(kwargs)
    return ns(**base)


def test_pdf_incluye_evidencias_despues_de_las_firmas(tmp_path):
    from PIL import Image as PilImage

    ruta = tmp_path / "trabajo.png"
    PilImage.new("RGB", (640, 360), (200, 30, 30)).save(ruta)

    piar = crear_piar_pdf_texto_extenso()
    piar.ajustes_razonables[0].evidencias = [
        _evidencia_ns(ruta, descripcion="Trabajo en clase"),
        _evidencia_ns(ruta, nombre_archivo="trabajo2.jpg", descripcion="Evaluación aplicada",
                      fecha=date(2026, 9, 12)),
    ]

    pdf = generate_piar_oficial_pdf(piar, None, [])
    documento = fitz.open(stream=pdf, filetype="pdf")
    textos = [pagina.get_text() for pagina in documento]
    indice_firmas = next(i for i, t in enumerate(textos) if "Firma de los Actores comprometidos" in t)
    indice_evidencias = next(i for i, t in enumerate(textos) if "EVIDENCIAS" in t)

    assert indice_evidencias > indice_firmas
    pagina = documento[indice_evidencias]
    contenido = pagina.get_text()
    assert pagina.rect.width > pagina.rect.height  # hoja horizontal
    assert "Asignatura - Docente" in contenido
    assert "Matemáticas" in contenido
    assert "Clara Gómez" in contenido
    assert "Trabajo en clase" in contenido
    assert "Evaluación aplicada" in contenido
    assert "10/09/2026" in contenido and "12/09/2026" in contenido
    assert pagina.get_images()
    anchos = [info["bbox"][2] - info["bbox"][0] for info in pagina.get_image_info()]
    assert max(anchos) > 300  # la evidencia se muestra más grande en horizontal


def test_pdf_no_muestra_evidencias_de_otro_periodo(tmp_path):
    from PIL import Image as PilImage

    ruta = tmp_path / "trabajo.png"
    PilImage.new("RGB", (200, 200), (0, 30, 200)).save(ruta)

    piar = crear_piar_pdf_texto_extenso()
    piar.ajustes_razonables[0].periodo_id = 2
    piar.ajustes_razonables[0].evidencias = [_evidencia_ns(ruta)]

    pdf = generate_piar_oficial_pdf(piar, None, [], periodo=NS(id=1))
    contenido = " ".join(
        (p.extract_text() or "") for p in PdfReader(BytesIO(pdf)).pages
    )
    assert "EVIDENCIAS" not in contenido
    assert "Trabajo en clase" not in contenido


def test_pdf_muestra_placeholder_cuando_falta_la_imagen(tmp_path):
    piar = crear_piar_pdf_texto_extenso()
    piar.ajustes_razonables[0].evidencias = [
        _evidencia_ns(tmp_path / "no_existe.png"),
        _evidencia_ns(tmp_path / "doc.pdf", tipo_archivo="pdf", nombre_archivo="doc.pdf"),
    ]

    pdf = generate_piar_oficial_pdf(piar, None, [])
    contenido = " ".join(
        (p.extract_text() or "") for p in PdfReader(BytesIO(pdf)).pages
    )
    assert "EVIDENCIAS" in contenido
    assert "Imagen no disponible" in contenido
    assert "Documento PDF: doc.pdf" in contenido

