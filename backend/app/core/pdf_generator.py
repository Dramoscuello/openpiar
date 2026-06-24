# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import io
import os
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.adapters.db.models import PiarORM, ConfiguracionSistemaORM, PeriodoAcademicoORM


def format_check_bool(val: Optional[bool]) -> str:
    if val is None:
        return "SI [  ]   NO [  ]"
    return "SI [X]   NO [  ]" if val else "SI [  ]   NO [X]"


def format_val(val, default="________________________") -> str:
    if val is None or val == "":
        return default
    return str(val)


def format_regimen(val: Optional[str]) -> str:
    if not val:
        return "Contributivo [  ]   Subsidiado [  ]"
    val_l = val.lower()
    c_check = "[X]" if "contrib" in val_l else "[  ]"
    s_check = "[X]" if "subsid" in val_l else "[  ]"
    return f"Contributivo {c_check}   Subsidiado {s_check}"


def format_jornada(val: Optional[str]) -> str:
    if not val:
        return "Mañana [  ]  Tarde [  ]  Única [  ]  Nocturna [  ]"
    v = val.lower()
    m = "[X]" if "mañ" in v else "[  ]"
    t = "[X]" if "tard" in v else "[  ]"
    u = "[X]" if "unic" in v or "únic" in v else "[  ]"
    n = "[X]" if "noct" in v else "[  ]"
    return f"Mañana {m}  Tarde {t}  Única {u}  Nocturna {n}"


def truncate_text(text: Optional[str], limit=1800) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "... [Texto truncado por espacio]"


def generate_acta_pdf(piar: PiarORM, config: Optional[ConfiguracionSistemaORM], periodos: list[PeriodoAcademicoORM]) -> bytes:
    """
    Genera el archivo PDF completo del PIAR (9 páginas) de un estudiante.
    Sigue fielmente la estructura y contenido del formato oficial del Decreto 1421 de 2017.
    """
    buffer = io.BytesIO()
    
    # Configuración de página con márgenes de 40 pt (aprox 1.4 cm)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=55
    )
    
    # Paleta de Colores
    primary_color = colors.HexColor("#1A365D")
    secondary_color = colors.HexColor("#4A5568")
    border_color = colors.HexColor("#CBD5E1")
    bg_light = colors.HexColor("#F8FAFC")
    
    # Estilos
    styles = getSampleStyleSheet()
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceAfter=2,
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=secondary_color,
        spaceAfter=2,
        alignment=1
    )
    
    anexo_style = ParagraphStyle(
        'DocAnexo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=primary_color,
        spaceAfter=12,
        alignment=1
    )
    
    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=primary_color,
        fontSize=10,
        leading=14,
        spaceBefore=8,
        spaceAfter=4
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        fontSize=8.5,
        leading=11
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8.5,
        leading=11
    )
    
    table_cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=primary_color
    )

    story = []
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assets_dir = os.path.join(base_dir, "assets")
    gobierno_path = os.path.join(assets_dir, "gobierno.png")
    minedu_path = os.path.join(assets_dir, "minedu.png")
    
    def get_header_table(anexo_num: str, title: str):
        logo_gobierno = None
        logo_minedu = None
        if os.path.exists(gobierno_path):
            logo_gobierno = Image(gobierno_path, width=194, height=22)
        if os.path.exists(minedu_path):
            logo_minedu = Image(minedu_path, width=80, height=22)

        header_data = []
        row = []
        
        if logo_gobierno:
            row.append(logo_gobierno)
        else:
            row.append("")
            
        if logo_minedu:
            row.append(logo_minedu)
        else:
            row.append("")
            
        right_text = Paragraph("<font color='#4A5568'><b>PIAR</b><br/>Decreto 1421/2017</font>", ParagraphStyle('HeaderRight', parent=body_style, fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=2))
        row.append(right_text)
        header_data.append(row)
        
        header_table = Table(header_data, colWidths=[210, 160, 162])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'LEFT'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        
        title_block = [
            header_table,
            Paragraph(title, title_style),
            Paragraph("Plan Individual de Ajustes Razonables – PIAR –", subtitle_style),
            Paragraph(anexo_num, anexo_style)
        ]
        return title_block

    estudiante = piar.estudiante
    grupo = estudiante.grupo
    grado_nombre = grupo.grado.nombre if (grupo and grupo.grado) else "No asignado"
    sede_nombre = grupo.sede.nombre if (grupo and grupo.sede) else "No asignada"
    inst_nombre = config.nombre_institucion if config else "INSTITUCIÓN EDUCATIVA"
    rector_nombre = config.nombre_rector if config else "No especificado"
    
    salud = estudiante.entorno_salud
    hogar = estudiante.entorno_hogar
    trayectoria = estudiante.trayectoria_educativa
    matricula = estudiante.matricula_actual
    caracteristicas = piar.caracteristicas
    
    story.extend(get_header_table("ANEXO 1", "INFORMACIÓN GENERAL DEL ESTUDIANTE Y ENTORNO DE SALUD"))
    story.append(Paragraph("1. INFORMACIÓN GENERAL DEL ESTUDIANTE", section_heading_style))
    
    victima_conflicto_str = format_check_bool(estudiante.victima_conflicto)
    registro_victima_str = format_check_bool(estudiante.registro_victima)
    en_centro_str = format_check_bool(estudiante.en_centro_proteccion)
    
    general_info_data = [
        [
            Paragraph(f"<b>Nombres:</b> {estudiante.nombres}", table_cell_style),
            Paragraph(f"<b>Apellidos:</b> {estudiante.apellidos}", table_cell_style),
            Paragraph(f"<b>Documento:</b> {estudiante.tipo_documento} {estudiante.numero_documento}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Fecha Nacimiento:</b> {estudiante.fecha_nacimiento.strftime('%d/%m/%Y')}", table_cell_style),
            Paragraph(f"<b>Edad:</b> {estudiante.edad} años", table_cell_style),
            Paragraph(f"<b>Lugar Nacimiento:</b> {format_val(estudiante.lugar_nacimiento)}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Dirección:</b> {estudiante.direccion}", table_cell_style),
            Paragraph(f"<b>Barrio / Vereda:</b> {estudiante.barrio_vereda}", table_cell_style),
            Paragraph(f"<b>Teléfono:</b> {format_val(estudiante.telefono)}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Correo:</b> {format_val(estudiante.correo)}", table_cell_style),
            Paragraph(f"<b>Grupo Étnico:</b> {format_val(estudiante.grupo_etnico, 'Ninguno')}", table_cell_style),
            Paragraph(f"<b>Grado al que Aspira:</b> {grado_nombre}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Víctima Conflicto:</b> {victima_conflicto_str}", table_cell_style),
            Paragraph(f"<b>Tiene Registro:</b> {registro_victima_str}", table_cell_style),
            Paragraph(f"<b>Centro Protección:</b> {en_centro_str} ({format_val(estudiante.centro_proteccion_donde, 'N/A')})", table_cell_style)
        ]
    ]
    
    t_gen_info = Table(general_info_data, colWidths=[177, 177, 178])
    t_gen_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_gen_info)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("2. ENTORNO SALUD", section_heading_style))
    
    salud_afiliacion = format_check_bool(salud.afiliacion_salud) if salud else "SI [  ]   NO [  ]"
    salud_eps = format_val(salud.eps) if salud else "No registrado"
    salud_regimen = format_regimen(salud.regimen) if salud else "Contributivo [  ]   Subsidiado [  ]"
    salud_emergencias = format_val(salud.lugar_emergencias) if salud else "No registrado"
    salud_atendido = format_check_bool(salud.atendido_sector_salud) if salud else "SI [  ]   NO [  ]"
    salud_frecuencia = format_val(salud.frecuencia_atencion_salud, "N/A") if salud else "No registrado"
    salud_diagnostico = format_check_bool(salud.tiene_diagnostico_medico) if salud else "SI [  ]   NO [  ]"
    salud_diag_cual = format_val(salud.diagnostico_medico, "Ninguno") if salud else "No registrado"
    salud_terapias = format_check_bool(salud.asiste_terapias) if salud else "SI [  ]   NO [  ]"
    
    terapias_list = salud.terapias_detalle if (salud and salud.terapias_detalle) else []
    terapias_str = ", ".join(terapias_list) if isinstance(terapias_list, list) else str(terapias_list)
    terapias_str = format_val(terapias_str, "Ninguna")
    
    salud_tratamiento = format_check_bool(salud.tratamiento_medico) if salud else "SI [  ]   NO [  ]"
    salud_trat_cual = format_val(salud.tratamiento_medico_cual, "N/A") if salud else "No registrado"
    salud_medicamentos = format_check_bool(salud.consume_medicamentos) if salud else "SI [  ]   NO [  ]"
    salud_med_cual = format_val(salud.medicamentos_detalle, "N/A") if salud else "No registrado"
    salud_apoyo = format_check_bool(salud.productos_apoyo_movilidad) if salud else "SI [  ]   NO [  ]"
    salud_apoyo_cual = format_val(salud.productos_apoyo_cual, "N/A") if salud else "No registrado"
    
    salud_info_data = [
        [
            Paragraph(f"<b>Afiliación Salud:</b> {salud_afiliacion}", table_cell_style),
            Paragraph(f"<b>EPS:</b> {salud_eps}", table_cell_style),
            Paragraph(f"<b>Régimen:</b> {salud_regimen}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Lugar Emergencias:</b> {salud_emergencias}", table_cell_style),
            Paragraph(f"<b>Atendido Sector Salud:</b> {salud_atendido}", table_cell_style),
            Paragraph(f"<b>Frecuencia Atención:</b> {salud_frecuencia}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Diagnóstico Médico:</b> {salud_diagnostico}", table_cell_style),
            Paragraph(f"<b>Detalle Diagnóstico:</b> {salud_diag_cual}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Asiste a Terapias:</b> {salud_terapias}", table_cell_style),
            Paragraph(f"<b>Cuáles Terapias:</b> {terapias_str}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Tratamiento Médico:</b> {salud_tratamiento}", table_cell_style),
            Paragraph(f"<b>Enfermedad Tratada:</b> {salud_trat_cual}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Toma Medicamentos:</b> {salud_medicamentos}", table_cell_style),
            Paragraph(f"<b>Cuáles Medicamentos:</b> {salud_med_cual}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Ayudas / Productos de Apoyo:</b> {salud_apoyo}", table_cell_style),
            Paragraph(f"<b>Cuáles Productos:</b> {salud_apoyo_cual}", table_cell_style),
            ""
        ]
    ]
    
    t_salud_info = Table(salud_info_data, colWidths=[177, 177, 178])
    t_salud_info.setStyle(TableStyle([
        ('SPAN', (1, 2), (2, 2)),
        ('SPAN', (1, 3), (2, 3)),
        ('SPAN', (1, 4), (2, 4)),
        ('SPAN', (1, 5), (2, 5)),
        ('SPAN', (1, 6), (2, 6)),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_salud_info)
    
    story.append(PageBreak())
    story.extend(get_header_table("ANEXO 1 (Continuación)", "ENTORNO HOGAR Y ENTORNO EDUCATIVO"))
    
    story.append(Paragraph("3. ENTORNO HOGAR", section_heading_style))
    
    h_madre = format_val(hogar.nombre_madre) if hogar else "No registrado"
    h_m_ocup = format_val(hogar.ocupacion_madre) if hogar else "No registrado"
    h_m_educ = format_val(hogar.nivel_educativo_madre) if hogar else "No registrado"
    
    h_padre = format_val(hogar.nombre_padre) if hogar else "No registrado"
    h_p_ocup = format_val(hogar.ocupacion_padre) if hogar else "No registrado"
    h_p_educ = format_val(hogar.nivel_educativo_padre) if hogar else "No registrado"
    
    h_cuid = format_val(hogar.nombre_cuidador, "N/A") if hogar else "No registrado"
    h_c_part = format_val(hogar.parentesco_cuidador, "N/A") if hogar else "No registrado"
    h_c_educ = format_val(hogar.nivel_educativo_cuidador, "N/A") if hogar else "No registrado"
    h_c_tel = format_val(hogar.telefono_cuidador, "N/A") if hogar else "No registrado"
    h_c_mail = format_val(hogar.correo_cuidador, "N/A") if hogar else "No registrado"
    
    h_vive_con = format_val(hogar.personas_vive_estudiante) if hogar else "No registrado"
    h_hermanos = format_val(hogar.numero_hermanos, "0") if hogar else "0"
    h_lugar_her = format_val(hogar.lugar_que_ocupa, "N/A") if hogar else "N/A"
    h_apoyo = format_val(hogar.apoyo_crianza, "Familia") if hogar else "No registrado"
    h_proteccion = format_check_bool(hogar.bajo_proteccion) if hogar else "SI [  ]   NO [  ]"
    h_subsidio = format_check_bool(hogar.recibe_subsidio) if hogar else "SI [  ]   NO [  ]"
    h_subsidio_cual = format_val(hogar.subsidio_cual, "N/A") if hogar else "No registrado"
    
    hogar_info_data = [
        [
            Paragraph(f"<b>Nombre de la Madre:</b> {h_madre}", table_cell_style),
            Paragraph(f"<b>Ocupación:</b> {h_m_ocup}", table_cell_style),
            Paragraph(f"<b>Educación:</b> {h_m_educ}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Nombre del Padre:</b> {h_padre}", table_cell_style),
            Paragraph(f"<b>Ocupación:</b> {h_p_ocup}", table_cell_style),
            Paragraph(f"<b>Educación:</b> {h_p_educ}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Nombre del Cuidador:</b> {h_cuid}", table_cell_style),
            Paragraph(f"<b>Parentesco:</b> {h_c_part}", table_cell_style),
            Paragraph(f"<b>Educación:</b> {h_c_educ}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Teléfono Cuidador:</b> {h_c_tel}", table_cell_style),
            Paragraph(f"<b>Correo Cuidador:</b> {h_c_mail}", table_cell_style),
            Paragraph(f"<b>Bajo Protección:</b> {h_proteccion}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Personas con quien vive:</b> {h_vive_con}", table_cell_style),
            Paragraph(f"<b>Hermanos:</b> {h_hermanos}", table_cell_style),
            Paragraph(f"<b>Lugar entre Hermanos:</b> {h_lugar_her}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Apoyos en Crianza:</b> {h_apoyo}", table_cell_style),
            Paragraph(f"<b>Recibe Subsidio:</b> {h_subsidio}", table_cell_style),
            Paragraph(f"<b>Cuál Subsidio:</b> {h_subsidio_cual}", table_cell_style)
        ]
    ]
    
    t_hogar_info = Table(hogar_info_data, colWidths=[177, 177, 178])
    t_hogar_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_hogar_info)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("4. ENTORNO EDUCATIVO", section_heading_style))
    
    tr_inicial = format_check_bool(trayectoria.vinculado_educacion_inicial) if trayectoria else "SI [  ]   NO [  ]"
    tr_inicial_inst = format_val(trayectoria.educacion_inicial_instituciones, "Ninguna") if trayectoria else "No registrado"
    tr_ultimo = format_val(trayectoria.ultimo_grado_cursado, "Ninguno") if trayectoria else "No registrado"
    tr_aprobo = format_check_bool(trayectoria.aprobo_ultimo_grado) if trayectoria else "SI [  ]   NO [  ]"
    tr_obs = format_val(trayectoria.observaciones_trayectoria, "Ninguna") if trayectoria else "No registrado"
    tr_informe = format_check_bool(trayectoria.recibe_informe_pedagogico) if trayectoria else "SI [  ]   NO [  ]"
    tr_informe_de = format_val(trayectoria.institucion_procedencia_informe, "N/A") if trayectoria else "No registrado"
    tr_complem = format_check_bool(trayectoria.asiste_programas_complementarios) if trayectoria else "SI [  ]   NO [  ]"
    tr_complem_cual = format_val(trayectoria.programas_complementarios_cuales, "N/A") if trayectoria else "No registrado"
    
    t_ie = format_val(matricula.institucion_educativa, inst_nombre) if matricula else inst_nombre
    t_sede = format_val(matricula.sede, sede_nombre) if matricula else sede_nombre
    t_grado = format_val(matricula.grado_ingreso, grado_nombre) if matricula else grado_nombre
    t_jornada = format_jornada(matricula.jornada) if matricula else "Mañana [  ]  Tarde [  ]  Única [  ]  Nocturna [  ]"
    t_transp = format_val(matricula.medio_transporte, "Común / Caminando") if matricula else "No registrado"
    t_dist = format_val(matricula.distancia_tiempo_hogar, "No registrado") if matricula else "No registrado"
    
    educ_info_data = [
        [
            Paragraph("<b>TRAYECTORIA EDUCATIVA</b>", table_cell_bold_style),
            "", ""
        ],
        [
            Paragraph(f"<b>Educación Inicial:</b> {tr_inicial}", table_cell_style),
            Paragraph(f"<b>Instituciones / Modalidad:</b> {tr_inicial_inst}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Último Grado Cursado:</b> {tr_ultimo}", table_cell_style),
            Paragraph(f"<b>¿Aprobó?:</b> {tr_aprobo}", table_cell_style),
            Paragraph(f"<b>Observaciones / Motivos de cambio:</b> {tr_obs}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Recibe informe cualitativo/PIAR previo:</b> {tr_informe}", table_cell_style),
            Paragraph(f"<b>Institución de procedencia del informe:</b> {tr_informe_de}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Asiste a programas complementarios:</b> {tr_complem}", table_cell_style),
            Paragraph(f"<b>Cuáles:</b> {tr_complem_cual}", table_cell_style),
            ""
        ],
        [
            Paragraph("<b>MATRÍCULA ACTUAL</b>", table_cell_bold_style),
            "", ""
        ],
        [
            Paragraph(f"<b>Nombre de la IE:</b> {t_ie}", table_cell_style),
            Paragraph(f"<b>Sede:</b> {t_sede}", table_cell_style),
            Paragraph(f"<b>Grado Ingreso:</b> {t_grado}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Jornada:</b> {t_jornada}", table_cell_style),
            "", ""
        ],
        [
            Paragraph(f"<b>Medio de Transporte:</b> {t_transp}", table_cell_style),
            Paragraph(f"<b>Tiempo / Distancia de viaje:</b> {t_dist}", table_cell_style),
            ""
        ]
    ]
    
    t_educ_info = Table(educ_info_data, colWidths=[177, 177, 178])
    t_educ_info.setStyle(TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (1, 1), (2, 1)),
        ('SPAN', (0, 5), (2, 5)),
        ('SPAN', (1, 3), (2, 3)),
        ('SPAN', (1, 4), (2, 4)),
        ('SPAN', (1, 7), (2, 7)),
        ('SPAN', (1, 8), (2, 8)),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_educ_info)
    
    story.append(PageBreak())
    story.extend(get_header_table("ANEXO 2", "VALORACIÓN PEDAGÓGICA Y CARACTERÍSTICAS DEL ESTUDIANTE"))
    
    # Tabla 1: Metadatos de la elaboración
    fecha_elab = piar.created_at.strftime("%d/%m/%Y") if piar.created_at else date.today().strftime("%d/%m/%Y")
    t_ie = format_val(matricula.institucion_educativa, inst_nombre) if matricula else inst_nombre
    t_sede = format_val(matricula.sede, sede_nombre) if matricula else sede_nombre
    jornada_text = matricula.jornada if (matricula and matricula.jornada) else "No asignada"
    docentes_text = format_val(piar.docentes_elaboran)

    meta_data = [
        [
            Paragraph(f"<b>Fecha de elaboración:</b> {fecha_elab}", table_cell_style),
            Paragraph(f"<b>Institución educativa:</b> {t_ie}", table_cell_style),
            Paragraph(f"<b>Sede:</b> {t_sede}", table_cell_style),
            Paragraph(f"<b>Jornada:</b> {jornada_text}", table_cell_style),
        ],
        [
            Paragraph(f"<b>Docentes que elaboran y cargo:</b> {docentes_text}", table_cell_style),
            "", "", ""
        ]
    ]
    meta_table = Table(meta_data, colWidths=[110, 170, 140, 112])
    meta_table.setStyle(TableStyle([
        ('SPAN', (0, 1), (3, 1)),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(Spacer(1, 8))
    story.append(meta_table)

    # Tabla 2: Datos del estudiante
    estudiante_nombre = f"{estudiante.nombres} {estudiante.apellidos}"
    doc_id = f"{estudiante.tipo_documento} {estudiante.numero_documento}"
    edad_text = f"{estudiante.edad} años"
    t_grado = format_val(matricula.grado_ingreso, grado_nombre) if matricula else grado_nombre

    est_data = [
        [
            Paragraph("<b>DATOS DEL ESTUDIANTE</b>", table_cell_bold_style),
            ""
        ],
        [
            Paragraph(f"<b>Nombre del estudiante:</b> {estudiante_nombre}", table_cell_style),
            Paragraph(f"<b>Documento de Identificación:</b> {doc_id}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Edad:</b> {edad_text}", table_cell_style),
            Paragraph(f"<b>Grado:</b> {t_grado}", table_cell_style)
        ]
    ]
    est_table = Table(est_data, colWidths=[266, 266])
    est_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), bg_light),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(Spacer(1, 8))
    story.append(est_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. CARACTERÍSTICAS DEL ESTUDIANTE", section_heading_style))
    
    desc_gustos = format_val(caracteristicas.descripcion_gustos_intereses) if caracteristicas else "No registrado"
    desc_habilidades = format_val(caracteristicas.descripcion_habilidades) if caracteristicas else "No registrado"
    
    box_p_style = ParagraphStyle('BoxText', parent=body_style, leading=14)
    box_t_style = ParagraphStyle('BoxTextTitle', parent=body_style, fontName='Helvetica-Bold', textColor=primary_color, spaceAfter=4)
    
    def get_text_box(label: str, content: str):
        box_data = [
            [Paragraph(label, box_t_style)],
            [Paragraph(content, box_p_style)]
        ]
        t = Table(box_data, colWidths=[532])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_light),
            ('BOX', (0,0), (-1,-1), 1, primary_color),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        return t

    story.append(get_text_box(
        "A) Descripción general del estudiante con énfasis en gustos e intereses o aspectos que le desagradan, expectativas del estudiante y la familia:",
        desc_gustos
    ))
    story.append(Spacer(1, 10))
    
    story.append(get_text_box(
        "B) Descripción en términos de lo que hace, puede hacer o requiere apoyo el estudiante para favorecer su proceso educativo:",
        desc_habilidades
    ))
    story.append(Spacer(1, 10))
    
    story.append(get_text_box(
        "C) Habilidades, competencias, cualidades, aprendizajes con las que cuenta el estudiante para el grado en el que fue matriculado:",
        "Habilidades del grado y competencias pedagógicas actuales registradas en la valoración institucional. "
        "Consulte los anexos complementarios de aula para detalles del estudiante."
    ))
    
    ajustes = piar.ajustes_razonables
    periodos_dict = {}
    
    for aj in ajustes:
        p_id = aj.periodo_id
        if p_id not in periodos_dict:
            periodos_dict[p_id] = []
        periodos_dict[p_id].append(aj)
        
    def build_matrix_page(period_name: str, period_ajustes: list):
        # Calcular la longitud máxima de un campo de texto para ajustar la fuente
        max_field_len = 0
        for aj in period_ajustes:
            field_lens = [
                len(aj.objetivos_propositos or ""),
                len(aj.barreras_evidenciadas or ""),
                len(aj.ajustes_estrategias or ""),
                len(aj.evaluacion_ajustes or "")
            ]
            if field_lens:
                max_field_len = max(max_field_len, max(field_lens))
            
        # Determinar tamaño de letra dinámico
        if max_field_len > 1800:
            f_size = 5.0
            l_size = 6.5
        elif max_field_len > 1200:
            f_size = 5.5
            l_size = 7.0
        elif max_field_len > 800:
            f_size = 6.5
            l_size = 8.0
        elif max_field_len > 400:
            f_size = 7.5
            l_size = 9.5
        else:
            f_size = 8.5
            l_size = 11.0
            
        dyn_cell_style = ParagraphStyle(
            'DynCell',
            parent=body_style,
            fontSize=f_size,
            leading=l_size
        )
        dyn_cell_bold_style = ParagraphStyle(
            'DynCellBold',
            parent=dyn_cell_style,
            fontName='Helvetica-Bold',
            textColor=primary_color
        )
        
        matrix_data = [
            [
                Paragraph("ÁREAS / APRENDIZAJES", table_header_style),
                Paragraph("OBJETIVOS / PROPÓSITOS (EBC y DBA)", table_header_style),
                Paragraph("BARRERAS EN EL CONTEXTO", table_header_style),
                Paragraph("AJUSTES RAZONABLES (Apoyos/Estrategias)", table_header_style),
                Paragraph("EVALUACIÓN DE LOS AJUSTES", table_header_style)
            ]
        ]
        
        if period_ajustes:
            # Agrupar ajustes por asignatura/área real de la base de datos
            ajustes_por_area = {}
            for aj in period_ajustes:
                area_name = aj.area.strip() if aj.area else "Otros"
                area_lower = area_name.lower()
                if area_lower not in ajustes_por_area:
                    ajustes_por_area[area_lower] = {
                        "display": area_name,
                        "list": []
                    }
                ajustes_por_area[area_lower]["list"].append(aj)
            
            # Ordenar las áreas/asignaturas alfabéticamente
            for area_lower in sorted(ajustes_por_area.keys()):
                area_info = ajustes_por_area[area_lower]
                area_display = area_info["display"]
                for aj in area_info["list"]:
                    tema = f"<b>{aj.titulo_tema}</b>: " if aj.titulo_tema else ""
                    # NO truncar textos: colocar todo el texto
                    obj_str = aj.objetivos_propositos or ""
                    bar_str = aj.barreras_evidenciadas or ""
                    aju_str = aj.ajustes_estrategias or ""
                    eva_str = aj.evaluacion_ajustes or "Pendiente de seguimiento"
                    
                    matrix_data.append([
                        Paragraph(f"<b>{area_display}</b>", dyn_cell_bold_style),
                        Paragraph(f"{tema}{obj_str}", dyn_cell_style),
                        Paragraph(bar_str, dyn_cell_style),
                        Paragraph(aju_str, dyn_cell_style),
                        Paragraph(eva_str, dyn_cell_style)
                    ])
        else:
            # Periodo sin ajustes registrados digitalmente
            # Listar todas las asignaturas de la carga académica del grupo
            carga_areas = []
            if piar.estudiante and piar.estudiante.grupo and piar.estudiante.grupo.carga:
                for item in piar.estudiante.grupo.carga:
                    if item.asignatura and item.asignatura.nombre:
                        carga_areas.append(item.asignatura.nombre)
            
            # Mantener unicidad y orden alfabético
            unique_areas = []
            seen = set()
            for area in carga_areas:
                area_clean = area.strip()
                if area_clean.lower() not in seen:
                    seen.add(area_clean.lower())
                    unique_areas.append(area_clean)
            unique_areas.sort()
            
            if unique_areas:
                for area in unique_areas:
                    matrix_data.append([
                        Paragraph(f"<b>{area}</b>", dyn_cell_bold_style),
                        Paragraph("________________________", dyn_cell_style),
                        Paragraph("________________________", dyn_cell_style),
                        Paragraph("________________________", dyn_cell_style),
                        Paragraph("________________________", dyn_cell_style)
                    ])
            else:
                # Fallback en caso de que no tenga carga académica asignada
                matrix_data.append([
                    Paragraph("<b>General</b>", dyn_cell_bold_style),
                    Paragraph("________________________", dyn_cell_style),
                    Paragraph("________________________", dyn_cell_style),
                    Paragraph("________________________", dyn_cell_style),
                    Paragraph("________________________", dyn_cell_style)
                ])
                
        matrix_table = Table(matrix_data, colWidths=[75, 114, 114, 114, 115], repeatRows=1)
        matrix_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('PADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ]))
        return matrix_table

    for p in periodos:
        story.append(PageBreak())
        p_name = p.nombre
        story.extend(get_header_table("ANEXO 2 (Seguimiento)", f"MATRIZ DE AJUSTES RAZONABLES - {p_name.upper()}"))
        story.append(Paragraph(f"Seguimiento de los Ajustes Pedagógicos - {p_name}", section_heading_style))
        
        current_ajustes = periodos_dict.get(p.id, [])
        story.append(build_matrix_page(p_name, current_ajustes))

    story.append(PageBreak())
    story.extend(get_header_table("ANEXO 2 (Mejoramiento)", "RECOMENDACIONES PARA EL PLAN DE MEJORAMIENTO INSTITUCIONAL (PMI)"))
    story.append(Paragraph("7. RECOMENDACIONES PARA LA ELIMINACIÓN DE BARRERAS (PMI)", section_heading_style))
    
    rec_pmi = piar.recomendaciones_pmi
    standard_actors = [
        "Familia, cuidadores o con quienes vive",
        "Docentes",
        "Directivos",
        "Administrativos",
        "Pares (Sus compañeros)"
    ]
    
    pmi_by_actor = {actor.lower(): [] for actor in standard_actors}
    
    for r in rec_pmi:
        act_lower = r.actor.lower() if r.actor else ""
        for std_actor in standard_actors:
            if act_lower in std_actor.lower() or std_actor.lower() in act_lower:
                pmi_by_actor[std_actor.lower()].append(r)
                break
                
    pmi_table_data = [
        [
            Paragraph("ACTORES", table_header_style),
            Paragraph("ACCIONES", table_header_style),
            Paragraph("ESTRATEGIAS A IMPLEMENTAR", table_header_style)
        ]
    ]
    
    for actor in standard_actors:
        recs = pmi_by_actor[actor.lower()]
        if not recs:
            pmi_table_data.append([
                Paragraph(f"<b>{actor}</b>", table_cell_bold_style),
                Paragraph("________________________________________", table_cell_style),
                Paragraph("________________________________________", table_cell_style)
            ])
        else:
            acciones = []
            estrategias = []
            for r in recs:
                acciones.append(r.acciones)
                estrategias.append(r.estrategias_implementar)
            pmi_table_data.append([
                Paragraph(f"<b>{actor}</b>", table_cell_bold_style),
                Paragraph("<br/><br/>".join(acciones), table_cell_style),
                Paragraph("<br/><br/>".join(estrategias), table_cell_style)
            ])
            
    pmi_table = Table(pmi_table_data, colWidths=[130, 201, 201])
    pmi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(pmi_table)
    story.append(Spacer(1, 10))
    
    val_firmas = []
    val_firmas.append(Paragraph("<b>Firmas del equipo de valoración pedagógica y diseño del PIAR:</b>", ParagraphStyle('ValTitle', parent=body_style, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=10)))
    
    val_signatures_data = [
        [
            Paragraph("<br/><br/>________________________________________<br/><b>Docente de Apoyo Pedagógico</b>", table_cell_style),
            Paragraph("<br/><br/>________________________________________<br/><b>Docente de Aula / Tutor</b>", table_cell_style),
            Paragraph("<br/><br/>________________________________________<br/><b>Directivo Docente (Coordinador/a)</b>", table_cell_style)
        ]
    ]
    val_table = Table(val_signatures_data, colWidths=[177, 177, 178])
    val_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    val_firmas.append(val_table)
    story.append(KeepTogether(val_firmas))

    story.append(PageBreak())
    story.extend(get_header_table("ANEXO 3", "ACTA DE ACUERDO Y CORRESPONSABILIDAD FAMILIAR"))
    
    fecha_firma_str = "_______"
    acta = piar.acta_acuerdo
    if acta and acta.fecha_firma:
        fecha_firma_str = acta.fecha_firma.strftime("%d/%m/%Y")
        
    docentes_nombres = piar.docentes_elaboran if piar.docentes_elaboran else "Docentes de Aula"
    
    nombre_familiar = "No especificado"
    parentesco_familiar = "No especificado"
    if estudiante.entorno_hogar:
        eh = estudiante.entorno_hogar
        if eh.nombre_cuidador:
            nombre_familiar = eh.nombre_cuidador
            parentesco_familiar = eh.parentesco_cuidador or "Cuidador(a)"
        elif eh.nombre_madre:
            nombre_familiar = eh.nombre_madre
            parentesco_familiar = "Madre"
        elif eh.nombre_padre:
            nombre_familiar = eh.nombre_padre
            parentesco_familiar = "Padre"

    info_data_acta = [
        [
            Paragraph(f"<b>Fecha:</b> {fecha_firma_str}", table_cell_style),
            Paragraph(f"<b>Institución educativa y Sede:</b> {inst_nombre} - {sede_nombre}", table_cell_style),
            ""
        ],
        [
            Paragraph(f"<b>Nombre del estudiante:</b> {estudiante.nombres} {estudiante.apellidos}", table_cell_style),
            Paragraph(f"<b>Documento de Identificación:</b> {estudiante.tipo_documento} {estudiante.numero_documento}", table_cell_style),
            Paragraph(f"<b>Edad / Grado:</b> {estudiante.edad} años / {grado_nombre}", table_cell_style)
        ],
        [
            Paragraph(f"<b>Nombres equipo directivos y de docentes:</b> {docentes_nombres} | Rector: {rector_nombre}", table_cell_style),
            "", "",
        ],
        [
            Paragraph(f"<b>Nombres familia del estudiante:</b> {nombre_familiar}", table_cell_style),
            "",
            Paragraph(f"<b>Parentesco:</b> {parentesco_familiar}", table_cell_style)
        ]
    ]

    info_table_acta = Table(info_data_acta, colWidths=[190, 190, 152])
    info_table_acta.setStyle(TableStyle([
        ('SPAN', (1, 0), (2, 0)),
        ('SPAN', (0, 2), (2, 2)),
        ('SPAN', (0, 3), (1, 3)),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(info_table_acta)
    story.append(Spacer(1, 10))
    
    intro_p1 = "Según el Decreto 1421 de 2017 la educación inclusiva es un proceso permanente que reconoce, valora y responde a la diversidad de características, intereses, posibilidades y expectativas de los estudiantes para promover su desarrollo, aprendizaje y participación, en un ambiente de aprendizaje común, sin discriminación o exclusión."
    intro_p2 = "La inclusión solo es posible cuando se unen los esfuerzos del colegio, el estudiante y la familia. De ahí la importancia de formalizar con las firmas, la presente Acta Acuerdo."
    intro_p3 = "El Establecimiento Educativo ha realizado la valoración y definido los ajustes razonables que facilitarán al estudiante su proceso educativo."
    intro_p4 = "La Familia se compromete a cumplir y firmar los compromisos señalados en el PIAR y en las actas de acuerdo, para fortalecer los procesos escolares del estudiante y en particular a:"
    
    story.append(Paragraph(intro_p1, body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(intro_p2, body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(intro_p3, body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(intro_p4, body_style))
    story.append(Spacer(1, 8))
    
    compromisos_aula = "No se han registrado compromisos específicos en el aula."
    if acta and acta.compromisos_aula:
        compromisos_aula = acta.compromisos_aula
        
    aula_title_style = ParagraphStyle(
        'AulaTitle',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=primary_color,
        spaceAfter=4
    )
    story.append(Paragraph("Compromisos específicos para el aula:", aula_title_style))
    aula_box_data = [[Paragraph(compromisos_aula, body_style)]]
    aula_table = Table(aula_box_data, colWidths=[532])
    aula_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(aula_table)
    
    story.append(PageBreak())
    story.append(Paragraph("<b>PIAR</b><br/>Decreto 1421/2017", ParagraphStyle('Page2Header', parent=body_style, fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=secondary_color)))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>Y en casa apoyará con las siguientes actividades:</b>", ParagraphStyle('HomeTitle', parent=body_style, fontName='Helvetica-Bold', fontSize=10, leading=13, spaceAfter=8)))
    
    compromisos_list = acta.compromisos_casa if (acta and acta.compromisos_casa) else []
    
    casa_table_data = [
        [
            Paragraph("Nombre de la Actividad", table_header_style),
            Paragraph("Descripción de la estrategia", table_header_style),
            Paragraph("Frecuencia (D: Diaria, S: Semanal, P: Permanente)", table_header_style)
        ]
    ]
    
    if len(compromisos_list) == 0:
        casa_table_data.append([
            Paragraph("________________________________________", table_cell_style),
            Paragraph("________________________________________________________________", table_cell_style),
            Paragraph("D __   S __   P __", table_cell_style)
        ])
    else:
        for c in compromisos_list:
            f = c.frecuencia.lower()
            d_check = "[X]" if f == "diaria" else "[  ]"
            s_check = "[X]" if f == "semanal" else "[  ]"
            p_check = "[X]" if f == "permanente" else "[  ]"
            frecuencia_str = f"D {d_check}    S {s_check}    P {p_check}"
            
            casa_table_data.append([
                Paragraph(c.nombre_actividad, table_cell_bold_style),
                Paragraph(c.descripcion_estrategia, table_cell_style),
                Paragraph(frecuencia_str, ParagraphStyle('FreqCell', parent=table_cell_style, fontName='Helvetica', fontSize=9, leading=11, alignment=1))
            ])
            
    casa_table = Table(casa_table_data, colWidths=[130, 260, 142])
    casa_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(casa_table)
    story.append(Spacer(1, 15))
    
    signatures = []
    signatures.append(Paragraph("<b>Firma de los Actores comprometidos (Firmas manuales):</b>", ParagraphStyle('SignTitle', parent=body_style, fontName='Helvetica-Bold', fontSize=10, leading=13, spaceAfter=15)))
    
    sig_cell_style = ParagraphStyle(
        'SigCell',
        parent=body_style,
        fontSize=8.5,
        leading=13,
        spaceAfter=15
    )
    
    signatures_data = [
        [
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>Firma del Estudiante</b><br/>"
                f"Nombre: {estudiante.nombres} {estudiante.apellidos}<br/>"
                f"Documento: {estudiante.tipo_documento} {estudiante.numero_documento}",
                sig_cell_style
            ),
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>Firma del Acudiente / Familia</b><br/>"
                f"Nombre: {nombre_familiar if nombre_familiar != 'No especificado' else '____________________________________'}<br/>"
                f"Parentesco: {parentesco_familiar if parentesco_familiar != 'No especificado' else '____________________'}<br/>"
                "Documento: ____________________________________",
                sig_cell_style
            )
        ],
        [
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>Firma Docente de Apoyo</b><br/>"
                "Nombre: ____________________________________<br/>"
                "Documento: ____________________________________",
                sig_cell_style
            ),
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>Firma Docente de Aula</b><br/>"
                f"Nombre: {docentes_nombres}<br/>"
                "Documento: ____________________________________",
                sig_cell_style
            )
        ],
        [
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>Firma Directivo Docente</b><br/>"
                f"Nombre: {rector_nombre}<br/>"
                "Cargo: Rector(a) / Coordinador(a)",
                sig_cell_style
            ),
            Paragraph("", sig_cell_style)
        ]
    ]
    
    signatures_table = Table(signatures_data, colWidths=[266, 266])
    signatures_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    signatures.append(signatures_table)
    story.append(KeepTogether(signatures))
    
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(40, 45, 572, 45)
        line1 = "V14.16/02/2018. - Ver documento de instrucciones."
        line2 = "Ministerio de Educación Nacional – Viceministerio de Educación Preescolar, Básica y Media – Decreto 1421 de 2017"
        canvas.drawString(40, 32, line1)
        canvas.drawString(40, 20, line2)
        page_num = canvas.getPageNumber()
        canvas.drawRightString(572, 20, f"Página {page_num}")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

