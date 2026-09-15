# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import io
import os
from datetime import date
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, LongTable, TableStyle, KeepTogether, PageBreak, NextPageTemplate, Image, HRFlowable
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


def _acta_del_periodo_pdf(piar, periodo):
    """Acta del periodo indicado; si no se especifica, la primera disponible."""
    actas = getattr(piar, "actas_acuerdo", None) or []
    if periodo is None:
        return actas[0] if actas else None
    return next((acta for acta in actas if acta.periodo_id == periodo.id), None)


def _ajustes_del_periodo_pdf(piar, periodo):
    """Ajustes razonables del periodo indicado; sin periodo, todos."""
    ajustes = getattr(piar, "ajustes_razonables", None) or []
    if periodo is None:
        return list(ajustes)
    return [ajuste for ajuste in ajustes if ajuste.periodo_id == periodo.id]


def _imagen_evidencia_para_pdf(ruta: Optional[str], caja=(130.0, 95.0)) -> Optional[Image]:
    """Convierte una imagen de evidencia en un flowable listo para incrustar.

    Normaliza formatos (PNG/WEBP/GIF/BMP/TIFF) a JPEG optimizado para no inflar
    el PDF y escala la imagen a la caja indicada sin ampliarla.
    """
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        from PIL import Image as PilImage

        with PilImage.open(ruta) as original:
            original.load()
            if original.mode in ("RGBA", "LA") or (
                original.mode == "P" and "transparency" in original.info
            ):
                rgba = original.convert("RGBA")
                fondo = PilImage.new("RGB", rgba.size, (255, 255, 255))
                fondo.paste(rgba, mask=rgba.split()[-1])
                imagen = fondo
            else:
                imagen = original.convert("RGB")

            imagen.thumbnail((600, 600))
            ancho_px, alto_px = imagen.size
            buffer = io.BytesIO()
            imagen.save(buffer, format="JPEG", quality=80)
    except Exception:
        return None

    if not ancho_px or not alto_px:
        return None
    escala = min(caja[0] / ancho_px, caja[1] / alto_px, 1.0)
    buffer.seek(0)
    return Image(buffer, width=ancho_px * escala, height=alto_px * escala)


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
    acta = piar.actas_acuerdo[0] if piar.actas_acuerdo else None
    if acta and acta.fecha_firma:
        fecha_firma_str = acta.fecha_firma.strftime("%d/%m/%Y")
        
    if grupo and grupo.director:
        docentes_nombres = f"{grupo.director.nombre} {grupo.director.apellido}"
    elif piar.docentes_elaboran:
        docentes_nombres = piar.docentes_elaboran
    else:
        docentes_nombres = "Docentes de Aula"
    
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

    # ─────────────────────────────────────
    # ANEXO 4: PORTAFOLIO DE EVIDENCIAS
    # ─────────────────────────────────────
    todas_evidencias = []
    for ajuste in piar.ajustes_razonables:
        for ev in (ajuste.evidencias or []):
            todas_evidencias.append((ajuste, ev))

    if todas_evidencias:
        story.append(PageBreak())
        story.extend(get_header_table("ANEXO 4", "PORTAFOLIO DE EVIDENCIAS DEL ESTUDIANTE"))
        story.append(Paragraph(
            "Evidencias de la implementación de los ajustes razonables DUA en el aula.",
            subtitle_style,
        ))
        story.append(Spacer(1, 12))

        row_items = []
        for ajuste, ev in todas_evidencias:
            area_text = ajuste.area
            periodo_nombre = ajuste.periodo.nombre if ajuste.periodo else "—"
            fecha_str = ev.fecha.strftime("%d/%m/%Y") if ev.fecha else ""
            creador = f"{ev.creador.nombre} {ev.creador.apellido}" if ev.creador else "—"

            if ev.tipo_archivo == "imagen" and os.path.exists(ev.ruta_archivo):
                try:
                    img = Image(ev.ruta_archivo, width=180, height=120)
                except Exception:
                    img = Paragraph(
                        '<font size="9" color="#94a3b8">[Imagen no disponible]</font>',
                        body_style,
                    )
            else:
                img = Paragraph(
                    '<font size="9" color="#64748b"><b>PDF</b><br/>'
                    f'{ev.nombre_archivo}</font>',
                    body_style,
                )

            info = Paragraph(
                f'<font size="8"><b>Área:</b> {area_text} | <b>Periodo:</b> {periodo_nombre}</font><br/>'
                f'<font size="8"><b>Fecha:</b> {fecha_str} | <b>Subido por:</b> {creador}</font><br/>'
                f'<font size="8.5">{ev.descripcion}</font>',
                body_style,
            )

            row_items.append([img, info])

        ev_table = Table(
            row_items,
            colWidths=[200, 332],
        )
        ev_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (1, 0), (1, -1), 12),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(ev_table)

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


def generate_auditoria_pdf(
    piar_id,
    auditoria_rows,
    config: Optional[ConfiguracionSistemaORM],
    estudiante: Any,
) -> bytes:
    """Genera un PDF de trazabilidad completa del PIAR con cabecera institucional."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=40, rightMargin=40,
        topMargin=40, bottomMargin=55,
    )

    primary_color = colors.HexColor("#1A365D")
    secondary_color = colors.HexColor("#4A5568")
    border_color = colors.HexColor("#CBD5E1")

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceAfter=2,
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=secondary_color,
        spaceAfter=2,
        alignment=1,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=primary_color,
        fontSize=10,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
    )
    entry_header_style = ParagraphStyle(
        "EntryHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=primary_color,
        spaceBefore=6,
        spaceAfter=2,
    )
    entry_body_style = ParagraphStyle(
        "EntryBody",
        parent=body_style,
        fontSize=8.5,
        leading=12,
    )
    entry_label_style = ParagraphStyle(
        "EntryLabel",
        parent=entry_body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#64748b"),
    )

    story: list = []

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assets_dir = os.path.join(base_dir, "assets")
    gobierno_path = os.path.join(assets_dir, "gobierno.png")
    minedu_path = os.path.join(assets_dir, "minedu.png")

    logo_gobierno = None
    logo_minedu = None
    if os.path.exists(gobierno_path):
        logo_gobierno = Image(gobierno_path, width=194, height=22)
    if os.path.exists(minedu_path):
        logo_minedu = Image(minedu_path, width=80, height=22)

    header_row: list = []
    header_row.append(logo_gobierno if logo_gobierno else "")
    header_row.append(logo_minedu if logo_minedu else "")
    right_text = Paragraph(
        "<font color='#4A5568'><b>AUDITORÍA</b><br/>Decreto 1421/2017</font>",
        ParagraphStyle(
            "HeaderRight", parent=body_style,
            fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=2,
        ),
    )
    header_row.append(right_text)

    header_table = Table([header_row], colWidths=[210, 160, 162])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "LEFT"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(header_table)

    institucion = config.nombre_institucion if config else "INSTITUCIÓN EDUCATIVA"
    story.append(Paragraph(institucion, title_style))
    story.append(Paragraph(
        f"NIT: {config.nit if config else ''} | DANE: {config.codigo_dane if config else ''}",
        subtitle_style,
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("REGISTRO DE TRAZABILIDAD — PIAR", title_style))
    story.append(Paragraph("Plan Individual de Ajustes Razonables — Decreto 1421 de 2017", subtitle_style))

    if estudiante:
        nombre = f"{getattr(estudiante, 'nombres', '')} {getattr(estudiante, 'apellidos', '')}"
        doc_id = getattr(estudiante, 'numero_documento', 'N/A')
        grado = getattr(getattr(estudiante, 'grupo', None), 'grado', None)
        grado_nombre = getattr(grado, 'nombre', '') if grado else ''
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<b>Estudiante:</b> {nombre} &nbsp;|&nbsp; "
            f"<b>Documento:</b> {doc_id} &nbsp;|&nbsp; "
            f"<b>Grado:</b> {grado_nombre or 'No asignado'}",
            entry_body_style,
        ))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Total de registros de auditoría:</b> {len(auditoria_rows)}",
        entry_body_style,
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("HISTORIAL CRONOLÓGICO DE CAMBIOS", section_style))
    story.append(Spacer(1, 6))

    etiquetas = {
        "ajuste_razonable": "Ajuste Razonable",
        "acta_acuerdo": "Acta de Acuerdo",
        "caracteristicas_estudiante": "Características del Estudiante",
        "compromiso_casa": "Compromiso Casa",
        "piar_estado": "Estado del PIAR",
        "piar_version": "Versión del PIAR",
        "evidencia_ajuste": "Evidencia del Ajuste",
    }
    acciones_labels = {"crear": "CREACIÓN", "modificar": "MODIFICACIÓN", "eliminar": "ELIMINACIÓN"}

    for i, entry in enumerate(auditoria_rows):
        tipo = etiquetas.get(entry.entidad_tipo, entry.entidad_tipo)
        accion = acciones_labels.get(entry.accion, entry.accion.upper())
        usuario = f"{entry.usuario.nombre} {entry.usuario.apellido}" if entry.usuario else "Sistema"
        fecha_str = entry.fecha.strftime("%d/%m/%Y %H:%M") if entry.fecha else ""

        entry_num = len(auditoria_rows) - i
        story.append(Paragraph(
            f'<font color="#1A365D"><b>#{entry_num}</b></font> '
            f'<b>{accion}</b> — {tipo}',
            entry_header_style,
        ))

        meta_row = [
            Paragraph(f"<b>Fecha:</b> {fecha_str}", entry_body_style),
            Paragraph(f"<b>Usuario:</b> {usuario}", entry_body_style),
            Paragraph(
                f"<b>ID Entrada:</b> {str(entry.id)[:8]}...",
                entry_body_style,
            ),
        ]
        meta_table = Table([meta_row], colWidths=[180, 200, 152])
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(meta_table)

        story.append(Spacer(1, 2))
        story.append(Table([
            [Spacer(1, 1)],
            [Spacer(1, 1)],
        ], colWidths=[532], rowHeights=[0.3, 0], style=[
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, border_color),
        ]))

        datos = entry.datos_nuevos or entry.datos_anteriores
        if datos:
            data_rows: list[list] = []
            for key, value in datos.items():
                if value is not None and str(value).strip():
                    label = key.replace("_", " ").upper()
                    val_str = str(value)[:250]
                    data_rows.append([
                        Paragraph(f"<b>{label}</b>", entry_label_style),
                        Paragraph(val_str, entry_body_style),
                    ])
            if data_rows:
                data_table = Table(data_rows, colWidths=[130, 402])
                data_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("LEFTPADDING", (1, 0), (1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ]))
                story.append(data_table)

        if entry.datos_anteriores and entry.datos_nuevos:
            story.append(Spacer(1, 3))
            story.append(Paragraph(
                '<font color="#64748b" size="8"><b>CAMPOS MODIFICADOS:</b></font>',
                entry_body_style,
            ))
            diff_rows: list[list] = []
            all_keys = set(list(entry.datos_anteriores.keys()) + list(entry.datos_nuevos.keys()))
            for key in sorted(all_keys):
                antes = entry.datos_anteriores.get(key)
                despues = entry.datos_nuevos.get(key)
                if antes != despues:
                    antes_str = str(antes)[:120] if antes is not None else "—"
                    despues_str = str(despues)[:120] if despues is not None else "—"
                    diff_rows.append([
                        Paragraph(f"<b>{key.replace('_', ' ').upper()}</b>", entry_label_style),
                        Paragraph(
                            f'<font color="#DC2626"><strike>{antes_str}</strike></font>',
                            entry_body_style,
                        ),
                        Paragraph(
                            f'<font color="#16A34A"><b>{despues_str}</b></font>',
                            entry_body_style,
                        ),
                    ])
            if diff_rows:
                diff_table = Table(diff_rows, colWidths=[120, 200, 212])
                diff_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(diff_table)

        story.append(Spacer(1, 10))

    def add_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(40, 45, 572, 45)
        canvas.drawString(40, 32, "OpenPiar — Registro de Auditoría")
        canvas.drawString(40, 20, "Ministerio de Educación Nacional – Decreto 1421 de 2017")
        page_num = canvas.getPageNumber()
        canvas.drawRightString(572, 20, f"Página {page_num}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes



def generate_piar_oficial_pdf(
    piar: PiarORM,
    config: Optional[ConfiguracionSistemaORM],
    periodos: list[PeriodoAcademicoORM],
    modo: str = "final",
    faltantes: Optional[list[str]] = None,
    periodo: Optional[PeriodoAcademicoORM] = None,
) -> bytes:
    """Genera el PDF completo del PIAR en formato oficial MEN Decreto 1421/2017 V15. 08/2020.
    Portrait para secciones 1-4, landscape para matriz de ajustes.
    Si se indica `periodo`, la matriz de ajustes y el acta corresponden a ese periodo."""

    buffer = io.BytesIO()

    frame_portrait = Frame(1.5*cm, 1.5*cm, letter[0] - 3*cm, letter[1] - 5*cm, id='p')
    tmpl_portrait = PageTemplate(id='Portrait', frames=[frame_portrait],
                                 onPage=lambda c,d: _header_footer(c, d, letter), pagesize=letter)

    from reportlab.lib.pagesizes import landscape
    ls_size = landscape(letter)
    frame_landscape = Frame(1.5*cm, 1.5*cm, ls_size[0] - 3*cm, ls_size[1] - 5*cm, id='l')
    tmpl_landscape = PageTemplate(id='Landscape', frames=[frame_landscape],
                                  onPage=lambda c,d: _header_footer(c, d, ls_size), pagesize=ls_size)

    doc = BaseDocTemplate(buffer, pagesize=letter, rightMargin=0, leftMargin=0, topMargin=0, bottomMargin=0)
    doc.addPageTemplates([tmpl_portrait, tmpl_landscape])

    navy = colors.HexColor('#1F3864')
    gris_label = colors.HexColor('#D9D9D9')
    gris_fondo = colors.HexColor('#f0f0f0')
    gris_header = colors.HexColor('#e0e0e0')
    gris_footer = colors.grey
    negro = colors.HexColor('#1a1a1a')

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    has_logo = os.path.exists(logo_path)

    def _header_footer(canvas, doc_obj, page_size):
        canvas.saveState()
        x_right = page_size[0] - 1.5*cm
        y_top = page_size[1] - 1*cm
        # Logo centrado verticalmente en el recuadro
        if has_logo:
            canvas.drawImage(logo_path, 1.6*cm, y_top - 38, width=130, height=28, preserveAspectRatio=True, mask='auto')
        # Texto PIAR / Decreto / 1421/2017 centrado verticalmente
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawRightString(x_right, y_top - 12, "PIAR")
        canvas.setFont('Helvetica-Bold', 7)
        canvas.drawRightString(x_right, y_top - 22, "Decreto")
        canvas.drawRightString(x_right, y_top - 30, "1421/2017")
        # Borde del header con padding interno
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.rect(1.5*cm, y_top - 52, page_size[0] - 3*cm, 52, stroke=1, fill=0)
        # Footer
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(gris_footer)
        canvas.drawCentredString(page_size[0]/2, 1.8*cm,
            u"V15. 08/2020. Ministerio de Educaci\u00f3n Nacional \u2013 Viceministerio de Educaci\u00f3n Preescolar, B\u00e1sica y Media \u2013 Decreto 1421 de 2017")
        if modo == "borrador":
            canvas.saveState()
            canvas.setFillColor(colors.Color(0.78, 0.78, 0.78, alpha=0.28))
            canvas.setFont("Helvetica-Bold", 58)
            canvas.translate(page_size[0] / 2, page_size[1] / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "BORRADOR")
            canvas.restoreState()
        canvas.restoreState()

    styles = getSampleStyleSheet()
    sty_hdr = ParagraphStyle('h', parent=styles['Normal'], fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
    sty_banner = ParagraphStyle('banner', parent=sty_hdr, fontSize=12, leading=16, alignment=TA_CENTER,
                                fontName='Helvetica-Bold', textColor=colors.white, spaceAfter=0, spaceBefore=0)
    sty_sec = ParagraphStyle('s', parent=styles['Normal'], fontSize=11, leading=13, alignment=TA_LEFT,
                             fontName='Helvetica-Bold', textColor=negro, spaceAfter=6, leftIndent=8, firstLineIndent=-8)
    sty_norm = ParagraphStyle('n', parent=styles['Normal'], fontSize=9, leading=11, alignment=TA_LEFT, spaceAfter=4)
    sty_c = ParagraphStyle('c', parent=styles['Normal'], fontSize=7.5, leading=9.5, alignment=TA_LEFT, spaceAfter=0)
    sty_cc = ParagraphStyle('cc', parent=styles['Normal'], fontSize=7.5, leading=9.5, alignment=TA_CENTER, spaceAfter=0)
    sty_cb = ParagraphStyle('cb', parent=sty_c, fontName='Helvetica-Bold')
    sty_cg = ParagraphStyle('cg', parent=sty_c, fontSize=6.5, leading=8, textColor=colors.HexColor('#808080'))
    sty_cb_white = ParagraphStyle('cbw', parent=sty_cb, textColor=colors.white)
    sty_ccw = ParagraphStyle('ccw', parent=sty_cc, textColor=colors.white)

    def P(text, style=sty_c):
        seguro = escape(str(text or "")).replace("\n", "<br/>")
        return Paragraph(seguro, style)

    def _table(data, widths, extra=None, repeat=0):
        t = Table(data, colWidths=widths, repeatRows=repeat)
        s = [
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ]
        if extra: s.extend(extra)
        t.setStyle(TableStyle(s))
        return t

    def _label_cell(text):
        """Celda de etiqueta con sombreado gris."""
        return {'bg': gris_label, 'text': P(text, sty_cb)}

    def _banner(title, ancho=16.2*cm):
        """Titulo tipo banner: fondo navy + texto blanco centrado."""
        t = Table([[P(title, sty_banner)]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), navy),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    story = []
    estudiante = piar.estudiante
    grupo = estudiante.grupo
    grado_nombre = grupo.grado.nombre if (grupo and grupo.grado) else ""
    sede_nombre = grupo.sede.nombre if (grupo and grupo.sede) else ""
    inst_nombre = config.nombre_institucion if config else ""
    salud = estudiante.entorno_salud
    hogar = estudiante.entorno_hogar
    trayectoria = estudiante.trayectoria_educativa
    matricula = estudiante.matricula_actual
    caracteristicas = piar.caracteristicas
    acta = _acta_del_periodo_pdf(piar, periodo)
    fecha_nac = estudiante.fecha_nacimiento.strftime("%d/%m/%Y") if estudiante.fecha_nacimiento else ""
    edad = None
    if estudiante.fecha_nacimiento:
        referencia = piar.fecha_creacion or date.today()
        edad = referencia.year - estudiante.fecha_nacimiento.year - (
            (referencia.month, referencia.day)
            < (estudiante.fecha_nacimiento.month, estudiante.fecha_nacimiento.day)
        )
    edad_str = f"{edad} a\u00f1os" if edad is not None else ""
    fecha_firma = (
        acta.fecha_firma.strftime("%d/%m/%Y")
        if (acta and acta.fecha_firma) else ""
    )
    fecha_diligenciamiento = fecha_firma or "DD/MM/AAAA"
    participantes = list(getattr(piar, "participantes", None) or [])
    docentes_texto = piar.docentes_elaboran or ""
    if participantes:
        docentes_texto = ", ".join(
            f"{item.nombre}{f' ({item.area})' if item.area else ''}"
            for item in participantes
        )
    primer_docente = docentes_texto.split(",")[0].strip() if docentes_texto else ""
    director = getattr(grupo, "director", None) if grupo else None
    director_nombre = " ".join(
        parte for parte in (
            getattr(director, "nombre", ""), getattr(director, "apellido", "")
        ) if parte
    ).strip()
    responsable_diligenciamiento = (
        f"{director_nombre} (Docente director de grupo)"
        if director_nombre else "Director de grupo no asignado"
    )
    direccion_institucion = getattr(config, "direccion", "") or ""

    # ═══════ BLOQUE 1: ENCABEZADO ═══════
    story.append(_banner("PLAN INDIVIDUAL DE AJUSTES RAZONABLES"))
    story.append(Spacer(1, 6))
    if modo == "borrador" and faltantes:
        pendiente_texto = "SECCIONES PENDIENTES: " + " | ".join(faltantes)
        pendiente = Table([[P(pendiente_texto, sty_c)]], colWidths=[16.2*cm])
        pendiente.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF2CC')),
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#A66A00')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(pendiente)
        story.append(Spacer(1, 6))
    data_top = [
        [_label_cell("Fecha y Lugar de Diligenciamiento"), P(f"{fecha_diligenciamiento}  {direccion_institucion}".strip(), sty_c)],
        [_label_cell("Nombre y rol de la Persona que diligencia"), P(responsable_diligenciamiento, sty_c)],
        [_label_cell("Instituci\u00f3n Educativa"), P(inst_nombre, sty_c)],
    ]
    # Construir tabla con celdas label con bg
    top_rows = []
    for label, val in data_top:
        lbl = label['text']
        bg = label['bg']
        top_rows.append([P(lbl.text, sty_cb), val])
    t_top = Table(top_rows, colWidths=[7*cm, 9.2*cm])
    t_top.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,-1), gris_label),
        ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.black),
        ('LINEAFTER', (0,0), (0,-1), 0.5, colors.black),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 8))

    # ═══════ BLOQUE 2: INFO GENERAL (8 cols) ═══════
    story.append(P(u"\u00a0\u00a0\u00a0\u00a01.\u00a0\u00a0\u00a0\u00a0Informaci\u00f3n general del estudiante", sty_sec))

    W = [3*cm, 1.8*cm, 1.8*cm, 1.8*cm, 2*cm, 2*cm, 1.6*cm, 2.2*cm]

    tipo_doc = estudiante.tipo_documento or "CC"
    con_vic = estudiante.registro_victima
    def _chk(yes):
        if yes is None:
            return '___'
        return '_x_' if yes else '___'

    def _si_no(valor):
        if valor is None:
            return "Si ___ No ___"
        return f"Si {_chk(valor)} No {_chk(not valor)}"
    proteccion = estudiante.en_centro_proteccion
    etnia = estudiante.grupo_etnico or ""

    info = [
        # Row 0: Nombres | Apellidos | Tipo ID | No. ID
        [P("Nombres", sty_cb), "", P("Apellidos", sty_cb), "", P("Tipo identificaci\u00f3n", sty_cb), "", P("No. de identificaci\u00f3n", sty_cb), ""],
        [P(estudiante.nombres or "", sty_c), "", P(estudiante.apellidos or "", sty_c), "",
         P("TI %s  CC %s  RC [ ]  otro__" % (_chk(tipo_doc=='TI'), _chk(tipo_doc=='CC')), sty_c), "",
         P(estudiante.numero_documento or "", sty_c), ""],

        # Row 2: Lugar nac | Edad | Fecha nac | Grado | Año anterior
        [P("Lugar de nacimiento", sty_cb), "", P("Edad", sty_cb), P("Fecha de nacimiento", sty_cb),
         P("Grado actual o al que ingresa:", sty_cb), "",
         P("El a\u00f1o anterior estuvo vinculado(a) al Sistema Educativo", sty_cb), ""],
        [P(estudiante.lugar_nacimiento or "", sty_c), "", P(edad_str, sty_c), P(fecha_nac, sty_c),
         P(grado_nombre, sty_c), "", P(_si_no(getattr(trayectoria, 'vinculado_sistema_anterior', None) if trayectoria else None), sty_c), ""],

        # Row 4: Depto | Municipio | Barrio/vereda
        [P("Departamento donde vive", sty_cb), P(estudiante.departamento_residencia or "", sty_c),
         P("Municipio", sty_cb), P(estudiante.municipio_residencia or "", sty_c),
         P("Barrio/vereda", sty_cb), "", P(estudiante.barrio_vereda or "", sty_c), ""],

        # Row 5: Dirección | Celular | Correo
        [P("Direcci\u00f3n de vivienda", sty_cb), P(estudiante.direccion or "", sty_c),
         P("Celular", sty_cb), P(estudiante.telefono or "", sty_c),
         P("Correo electr\u00f3nico", sty_cb), "", P(estudiante.correo or "", sty_c), ""],

        # Row 6: Víctima + registro | Centro protección | Grupo étnico
        [P(u"\u00bfSe reconoce como v\u00edctima del conflicto armado?", sty_cb),
         P(f"{_si_no(estudiante.victima_conflicto)}\n(Cuenta con el respectivo registro? {_si_no(con_vic)})", sty_c),
         P(u"\u00bfEst\u00e1 en alg\u00fan Centro de Protecci\u00f3n?", sty_cb),
         P(f"{_si_no(proteccion)} \u00bfCu\u00e1l? {estudiante.centro_proteccion_donde or ''}", sty_c),
         P(u"\u00bfSe reconoce o pertenece a un grupo \u00e9tnico?", sty_cb),
         P("", sty_c),
         P(f"{_si_no(getattr(estudiante, 'pertenece_grupo_etnico', None))} \u00bfCu\u00e1l? {etnia}", sty_c),
         P("", sty_c)],
        # Row 7 (contenida en las celdas de row 6, esta fila extra vacía para espaciado)
        [P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c)],
    ]

    # Lateral description rows
    _lbl = u"Descripci\u00f3n general del estudiante con \u00e9nfasis en sus capacidades, gustos e intereses o aspectos que le desagradan, expectativas del estudiante y la familia, acompa\u00f1amiento familiar y redes de apoyo con los que se cuenta."
    info.append([P(_lbl, sty_cb), P("", sty_c), P("Capacidades", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P(caracteristicas.descripcion_habilidades or "" if caracteristicas else "", sty_c), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P("Gustos e intereses", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P(caracteristicas.descripcion_gustos_intereses or "" if caracteristicas else "", sty_c), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P("Expectativas del estudiante", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P((caracteristicas.expectativas_estudiante or "") if (caracteristicas and hasattr(caracteristicas, 'expectativas_estudiante')) else "", sty_c), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P("Expectativas de la familia", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P((caracteristicas.expectativas_familia or "") if (caracteristicas and hasattr(caracteristicas, 'expectativas_familia')) else "", sty_c), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P("Redes de apoyo", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P((caracteristicas.entorno_familiar_social_economico or "") if (caracteristicas and hasattr(caracteristicas, 'entorno_familiar_social_economico')) else "", sty_c), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P("Otras", sty_cb), "", "", "", "", ""])
    info.append([P("", sty_c), P("", sty_c), P((caracteristicas.otras_observaciones or "") if (caracteristicas and hasattr(caracteristicas, 'otras_observaciones')) else "", sty_c), "", "", "", "", ""])

    spans_info = [
        # Row 0: Nombres(0-1) | Apellidos(2-3) | Tipo ID(4-5) | No. ID(6-7)
        ('SPAN', (0,0), (1,0)), ('SPAN', (2,0), (3,0)), ('SPAN', (4,0), (5,0)), ('SPAN', (6,0), (7,0)),
        # Row 1: spans same as row 0
        ('SPAN', (0,1), (1,1)), ('SPAN', (2,1), (3,1)), ('SPAN', (4,1), (5,1)), ('SPAN', (6,1), (7,1)),
        # Row 2: Lugar(0-1) | Edad(2) | Fecha(3) | Grado(4-5) | Año ant(6-7)
        ('SPAN', (0,2), (1,2)), ('SPAN', (4,2), (5,2)), ('SPAN', (6,2), (7,2)),
        # Row 3: same as row 2
        ('SPAN', (0,3), (1,3)), ('SPAN', (4,3), (5,3)), ('SPAN', (6,3), (7,3)),
        # Row 4: Depto(0) | Municipio(2) | Barrio(4) + data spans
        ('SPAN', (4,4), (5,4)), ('SPAN', (6,4), (7,4)),
        # Row 5: Dirección(0) | Celular(2) | Correo(4) + data spans
        ('SPAN', (4,5), (5,5)), ('SPAN', (6,5), (7,5)),
        # Row 6: etiquetas y respuestas separadas; etnia ocupa dos columnas por celda.
        ('SPAN', (4,6), (5,6)), ('SPAN', (6,6), (7,6)),
        # Row 7
        ('SPAN', (0,7), (7,7)),
        # Lateral rowspan: col 0-1, rows 8-19
        ('SPAN', (0,8), (1,19)),
    ]
    for r in range(8, 19, 2):
        if r < len(info): spans_info.append(('SPAN', (2, r), (7, r)))
    for r in range(9, 20, 2):
        if r < len(info): spans_info.append(('SPAN', (2, r), (7, r)))
    # Sombreado gris en filas de label
    label_rows = [0, 2, 4, 5, 6, 8]
    for lr in label_rows:
        for c in range(8):
            spans_info.append(('BACKGROUND', (c, lr), (c, lr), gris_label))

    t_info = Table(info, colWidths=W)
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ] + spans_info))
    story.append(t_info)
    story.append(Spacer(1, 6))

    # ═══════ BLOQUE 3: SALUD ═══════
    story.append(PageBreak())
    story.append(P(u"\u00a0\u00a0\u00a0\u00a02.\u00a0\u00a0\u00a0\u00a0Entorno Salud", sty_sec))

    afil_ok = salud.afiliacion_salud if salud else False
    regimen_ok = (salud.regimen or "").lower() if salud else ""
    subs = regimen_ok == "subsidiado"
    contrib = regimen_ok == "contributivo"
    tiene_diag = salud.tiene_diagnostico_medico if salud else False
    tiene_med = salud.consume_medicamentos if salud else False
    tiene_apoyo = (salud.productos_apoyo_movilidad if salud else False)
    px = _chk

    WS = [3.5*cm, 2*cm, 2*cm, 2.5*cm, 1.8*cm, 1.8*cm, 2.4*cm]
    atencion_med = salud.atendido_sector_salud if salud else False
    asiste_ter = salud.asiste_terapias if salud else False
    tiene_med = salud.consume_medicamentos if salud else False
    tiene_apoyo = (salud.productos_apoyo_movilidad if salud else False)
    px = _chk

    # Preparar listas JSONB para sub-filas
    am_list = (salud.atenciones_medicas if (salud and hasattr(salud, 'atenciones_medicas') and salud.atenciones_medicas) else [])
    if not isinstance(am_list, list): am_list = []
    while len(am_list) < 3: am_list.append({"cual": "", "frecuencia": ""})

    tp_list = (salud.terapias_detalle if (salud and salud.terapias_detalle) else [])
    if not isinstance(tp_list, list): tp_list = []
    while len(tp_list) < 3: tp_list.append({"tipo": "", "frecuencia": ""})

    med_list = (salud.medicamentos_lista if (salud and hasattr(salud, 'medicamentos_lista') and salud.medicamentos_lista) else [])
    if not isinstance(med_list, list): med_list = []
    while len(med_list) < 2: med_list.append({"cual": "", "frecuencia": ""})

    salud_data = [
        # Afiliación
        [P(u"Afiliaci\u00f3n al sistema de salud", sty_cb), P(_si_no(afil_ok), sty_c),
         P("Régimen", sty_cb),
         P(f"Contributivo {px(contrib)}\nSubsidiado {px(subs)}", sty_c),
         P("¿Cuál?", sty_cb), P(salud.eps or '' if salud else '', sty_c), P("", sty_c)],
        # Lugar emergencias
        [P("Lugar donde le atienden en caso de emergencia", sty_cb),
         P(salud.lugar_emergencias or "" if salud else "", sty_c),
         P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c), P("", sty_c)],
        # Diagnóstico
        [P(u"Cuenta con diagn\u00f3stico m\u00e9dico", sty_cb),
         P("Si %s No___" % (px(tiene_diag)), sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb),
         P(salud.diagnostico_medico or "" if salud else "", sty_c),
         P("", sty_c), P("", sty_c), P("", sty_c)],

        # Atención médica (rowspan 3)
        [P(u"Cuenta con atenci\u00f3n m\u00e9dica", sty_cb),
         P("Si %s No___" % (px(atencion_med)), sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb),
         P(am_list[0].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb),
         P(am_list[0].get("frecuencia", ""), sty_c),
         P("", sty_c)],
        [P("", sty_c), P("", sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb), P(am_list[1].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb), P(am_list[1].get("frecuencia", ""), sty_c), P("", sty_c)],
        [P("", sty_c), P("", sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb), P(am_list[2].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb), P(am_list[2].get("frecuencia", ""), sty_c), P("", sty_c)],

        # Intervención terapéutica (rowspan 3)
        [P(u"Cuenta con intervenci\u00f3n o tratamiento terap\u00e9utico integral", sty_cb),
         P("Si %s No___" % (px(asiste_ter)), sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb),
         P(tp_list[0].get("tipo", "") or tp_list[0].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb),
         P(tp_list[0].get("frecuencia", ""), sty_c),
         P("", sty_c)],
        [P("", sty_c), P("", sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb),
         P(tp_list[1].get("tipo", "") or tp_list[1].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb),
         P(tp_list[1].get("frecuencia", ""), sty_c),
         P("", sty_c)],
        [P("", sty_c), P("", sty_c),
         P(u"\u00bfCu\u00e1l?", sty_cb),
         P(tp_list[2].get("tipo", "") or tp_list[2].get("cual", ""), sty_c),
         P("Frecuencia", sty_cb),
         P(tp_list[2].get("frecuencia", ""), sty_c),
         P("", sty_c)],

        # Medicamentos (rowspan 2)
        [P(u"\u00bfConsume medicamentos?", sty_cb),
         P("Si %s No %s" % (px(tiene_med), px(not tiene_med)), sty_c),
         P(u"\u00bfCu\u00e1les?", sty_cb),
         P(med_list[0].get("cual", ""), sty_c),
         P("Frecuencia y horario", sty_cb),
         P(med_list[0].get("frecuencia", ""), sty_c),
         P("", sty_c)],
        [P("", sty_c), P("", sty_c),
         P(u"\u00bfCu\u00e1les?", sty_cb),
         P(med_list[1].get("cual", ""), sty_c),
         P("Frecuencia y horario", sty_cb),
         P(med_list[1].get("frecuencia", ""), sty_c),
         P("", sty_c)],

        # Apoyos
        [P(u"\u00bfCuenta con apoyos o ayudas t\u00e9cnicas o tecnol\u00f3gicas para favorecer su movilidad, comunicaci\u00f3n e independencia?", sty_cb),
         P("Si %s No %s" % (px(tiene_apoyo), px(not tiene_apoyo)), sty_c),
         P(u"\u00bfCu\u00e1les?", sty_cb),
         P(salud.productos_apoyo_cual or "" if salud else "", sty_c),
         P("", sty_c), P("", sty_c), P("", sty_c)],
    ]
    ss = [
        ('SPAN', (5,0), (6,0)),  # EPS: valor separado de la etiqueta ¿Cuál?
        ('BACKGROUND', (2,0), (2,0), gris_label),
        ('BACKGROUND', (4,0), (4,0), gris_label),
        ('SPAN', (1,1), (6,1)),  # Lugar emergencias
        ('SPAN', (3,2), (6,2)),  # Diagnóstico ¿Cuál?
        # Atención médica rowspans
        ('SPAN', (0,3), (0,5)), ('SPAN', (1,3), (1,5)),
        # Intervención rowspans
        ('SPAN', (0,6), (0,8)), ('SPAN', (1,6), (1,8)),
        # Medicamentos rowspans
        ('SPAN', (0,9), (0,10)), ('SPAN', (1,9), (1,10)),
        # Apoyos
        ('SPAN', (3,11), (6,11)),
    ]
    # Sombreado gris en labels
    for r in range(len(salud_data)):
        ss.append(('BACKGROUND', (0, r), (0, r), gris_label))
    # También gris en labels de sub-filas (¿Cuál?, Frecuencia)
    for r in [3,4,5,6,7,8,9,10]:
        if r < len(salud_data):
            ss.append(('BACKGROUND', (2, r), (2, r), gris_label))
            ss.append(('BACKGROUND', (4, r), (4, r), gris_label))
    t_salud = Table(salud_data, colWidths=WS)
    t_salud.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ] + ss))
    story.append(t_salud)
    story.append(Spacer(1, 8))

    # ═══════ BLOQUE 4: HOGAR ═══════
    story.append(P(u"\u00a0\u00a0\u00a0\u00a03.\u00a0\u00a0\u00a0\u00a0Entorno Hogar", sty_sec))
    WH = [4*cm, 4*cm, 4*cm, 4*cm]
    def _h(s):
        return str(hogar and getattr(hogar, s, None) or '')

    hogar_data = [
        [P("Nombre de la madre", sty_cb), P(_h('nombre_madre'), sty_c),
         P("Nombre del padre", sty_cb), P(_h('nombre_padre'), sty_c)],
        [P(u"Ocupaci\u00f3n de la madre", sty_cb), P(_h('ocupacion_madre'), sty_c),
         P(u"Ocupaci\u00f3n del padre", sty_cb), P(_h('ocupacion_padre'), sty_c)],
        [P("Nivel educativo madre", sty_cb), P("%s  %s" % ("Prim/Bto/T\u00e9c/Tecn/univ.", _h('nivel_educativo_madre')), sty_c),
         P("Nivel educativo padre", sty_cb), P("%s  %s" % ("Prim/Bto/T\u00e9c/Tecn/univ.", _h('nivel_educativo_padre')), sty_c)],
        [P("Nombre Cuidador", sty_cb), P(_h('nombre_cuidador'), sty_c),
         P("Nivel educativo cuidador", sty_cb), P("Prim/Bto/T\u00e9c/Tecn/univ.  " + _h('nivel_educativo_cuidador'), sty_c)],
        [P("Parentesco del cuidador", sty_cb), P(_h('parentesco_cuidador'), sty_c),
         P("Celular", sty_cb), P(_h('telefono_cuidador'), sty_c)],
        [P(u"Correo electr\u00f3nico", sty_cb), P(_h('correo_cuidador'), sty_c),
         P("Personas con quien vive", sty_cb), P(_h('personas_vive_estudiante'), sty_c)],
        [P("No. Hermanos", sty_cb), P(str(hogar.numero_hermanos) if hogar else "", sty_c),
         P("Lugar que ocupa", sty_cb), P(str(hogar.lugar_que_ocupa) if (hogar and hogar.lugar_que_ocupa) else "", sty_c)],
        [P(u"\u00bfQui\u00e9nes apoyan la crianza del estudiante?", sty_cb), P(_h('apoyo_crianza'), sty_c),
         P("", sty_c), P("", sty_c)],
    ]
    hs_labels = []
    for r in range(len(hogar_data)):
        hs_labels.append(('BACKGROUND', (0, r), (0, r), gris_label))
        hs_labels.append(('BACKGROUND', (2, r), (2, r), gris_label))
    hs_labels.append(('SPAN', (2, 7), (3, 7)))

    t_hogar = Table(hogar_data, colWidths=WH)
    t_hogar.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ] + hs_labels))
    story.append(t_hogar)
    story.append(Spacer(1, 8))

    # ═══════ BLOQUE 5: EDUCATIVO ═══════
    titulo_educativo = P(u"\u00a0\u00a0\u00a0\u00a04.\u00a0\u00a0\u00a0\u00a0Entorno Educativo", sty_sec)
    WE = [4*cm, 3*cm, 3*cm, 3*cm, 3.1*cm]
    trayect_vin = trayectoria.vinculado_educacion_inicial if trayectoria else None
    estado_ultimo = getattr(trayectoria, 'estado_ultimo_grado', None) if trayectoria else None
    recibe_inf = trayectoria.recibe_informe_pedagogico if trayectoria else False
    asiste_prog = bool(getattr(trayectoria, 'asiste_programas_complementarios', False))
    programas_texto = format_check_bool(asiste_prog)
    if asiste_prog:
        programas_texto += "\n¿Cuáles? " + (trayectoria.programas_complementarios_cuales or "")

    edu_data = [
        [P(u"\u00bfHa estado vinculado en otra instituci\u00f3n educativa, fundaci\u00f3n o bajo otra modalidad de educaci\u00f3n?", sty_cb),
         P("", sty_c), P("No___ \u00bfPor qu\u00e9?" if not trayect_vin else "", sty_c),
         P("SI %s" % (_chk(trayect_vin)), sty_c),
         P(u"\u00bfCu\u00e1les? %s" % (trayectoria.educacion_inicial_instituciones or '' if trayectoria else ''), sty_c)],
        [P(u"\u00daltimo grado cursado", sty_cb),
         P(trayectoria.ultimo_grado_cursado or "" if trayectoria else "", sty_c),
         P("Estado", sty_cb),
         P("Aprobado %s  Reprobado %s  Sin terminar %s" % (
             _chk(estado_ultimo == 'aprobado'),
             _chk(estado_ultimo == 'reprobado'),
             _chk(estado_ultimo == 'sin_terminar'),
         ), sty_c),
         P("Observaciones: %s" % (trayectoria.observaciones_trayectoria or '' if trayectoria else ''), sty_c)],
        [P(u"\u00bfSe recibe informe pedag\u00f3gico cualitativo o certificado que describa el proceso de desarrollo y aprendizaje del estudiante y/o PIAR?", sty_cb),
         P("", sty_c), P("", sty_c),
         P("Si %s  No %s" % (_chk(recibe_inf), _chk(not recibe_inf)), sty_c), P("", sty_c)],
        [P(u"\u00bfDe qu\u00e9 instituci\u00f3n o modalidad proviene el informe?", sty_cb),
         P("", sty_c),
         P(trayectoria.institucion_procedencia_informe or "" if trayectoria else "", sty_c),
         P("", sty_c), P("", sty_c)],
        [P(u"\u00bfEst\u00e1 asistiendo en la actualidad a programas complementarios?", sty_cb),
         P("", sty_c), P(programas_texto, sty_c), P("", sty_c), P("", sty_c)],
    ]
    es = [
        ('SPAN', (0,0), (1,0)), ('SPAN', (4,0), (4,0)),
        ('SPAN', (0,1), (0,1)), ('SPAN', (4,1), (4,1)),
        ('SPAN', (0,2), (2,2)), ('SPAN', (3,2), (4,2)),
        ('SPAN', (0,3), (1,3)), ('SPAN', (2,3), (4,3)),
        ('SPAN', (0,4), (1,4)), ('SPAN', (2,4), (4,4)),
    ]
    for r in range(len(edu_data)):
        es.append(('BACKGROUND', (0, r), (0, r), gris_label))
        if r == 1 or r == 2:
            es.append(('BACKGROUND', (2, r), (2, r), gris_label))

    t_edu = Table(edu_data, colWidths=WE)
    t_edu.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ] + es))
    # ═══════ FIRMAS INICIALES ═══════
    firmas_ini = [
        [P("Nombre y firma de quien diligencia", sty_cb), P("Nombre y firma acudiente", sty_cb)],
        [P("", sty_c), P("", sty_c)],
    ]
    t_fi = Table(firmas_ini, colWidths=[sum(WE)/2, sum(WE)/2], rowHeights=[None, 2*cm])
    t_fi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), gris_label), ('BACKGROUND', (1,0), (1,0), gris_label),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    # Mantener el entorno educativo junto a sus firmas físicas cuando cabe en una página.
    story.append(KeepTogether([titulo_educativo, t_edu, Spacer(1, 8), t_fi]))
    story.append(Spacer(1, 6))

    # ═══════ CARACTERIZACION PEDAGOGICA ═══════
    story.append(PageBreak())
    story.append(_banner("PLAN INDIVIDUAL DE AJUSTES RAZONABLES - PIAR -"))
    story.append(Spacer(1, 4))
    story.append(_banner("ANEXO 2"))
    story.append(Spacer(1, 6))
    docentes_agrupados = {}
    for item in participantes:
        nombre = " ".join(item.nombre.split())
        docente = docentes_agrupados.setdefault(
            nombre.casefold(), {"nombre": nombre, "cargos": {}, "areas": {}}
        )
        cargo = " ".join((getattr(item, 'cargo', None) or item.rol_piar.replace('_', ' ')).split())
        docente["cargos"].setdefault(cargo.casefold(), cargo)
        area = " ".join((getattr(item, 'area', None) or "").split())
        if area:
            docente["areas"].setdefault(area.casefold(), area)
    participantes_texto = "\n".join(
        " - ".join(parte for parte in (
            docente["nombre"], ", ".join(docente["cargos"].values()),
            ", ".join(docente["areas"].values()),
        ) if parte)
        for docente in docentes_agrupados.values()
    ) or docentes_texto
    anexo2_meta = [
        [P("Fecha de elaboración", sty_cb), P(fecha_diligenciamiento, sty_c),
         P("Institución educativa", sty_cb), P(inst_nombre, sty_c)],
        [P("Sede", sty_cb), P(sede_nombre, sty_c),
         P("Grado", sty_cb), P(grado_nombre, sty_c)],
        [P("Docentes que elaboran y cargo", sty_cb), P(participantes_texto, sty_c), "", ""],
    ]
    t_meta = Table(anexo2_meta, colWidths=[3.5*cm, 4.5*cm, 3.5*cm, 4.7*cm])
    t_meta.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (0,-1), gris_label),
        ('BACKGROUND', (2,0), (2,1), gris_label),
        ('SPAN', (1,2), (3,2)),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    def _titulo_anexo2(texto):
        titulo = _banner(texto)
        titulo.keepWithNext = True
        return titulo

    def _contenido_anexo2(parrafos):
        # Una sola celda con margen interior, divisible si el texto ocupa varias páginas.
        tabla = Table([[parrafos]], colWidths=[16.2*cm], splitInRow=1)
        tabla.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        return tabla

    story.append(_titulo_anexo2("DATOS DEL ESTUDIANTE"))
    story.append(_table([
        [P("Nombre del estudiante", sty_cb), P(f"{estudiante.nombres} {estudiante.apellidos}", sty_c),
         P("Documento de identificación", sty_cb), P(estudiante.numero_documento, sty_c)],
        [P("Edad", sty_cb), P(edad_str, sty_c), P("Grado", sty_cb), P(grado_nombre, sty_c)],
    ], [3.8*cm, 4.6*cm, 4*cm, 3.8*cm], [
        ('BACKGROUND', (0,0), (0,-1), gris_label),
        ('BACKGROUND', (2,0), (2,-1), gris_label),
    ]))
    story.append(Spacer(1, 6))
    story.append(_titulo_anexo2("1. CARACTERÍSTICAS DEL ESTUDIANTE"))
    story.append(_contenido_anexo2([P("Entorno familiar, social y económico", sty_cb), P(
        caracteristicas.entorno_familiar_social_economico
        if caracteristicas and caracteristicas.entorno_familiar_social_economico
        else "No registrado",
        sty_norm,
    )]))
    story.append(Spacer(1, 6))
    story.append(_titulo_anexo2("Caracterizaci\u00f3n pedag\u00f3gica o diagn\u00f3stico"))
    if caracteristicas and hasattr(caracteristicas, 'caracterizacion_pedagogica') and caracteristicas.caracterizacion_pedagogica:
        texto_caracterizacion = caracteristicas.caracterizacion_pedagogica
    elif caracteristicas and caracteristicas.descripcion_habilidades:
        texto_caracterizacion = caracteristicas.descripcion_habilidades
    else:
        texto_caracterizacion = "No registrada"
    story.append(_contenido_anexo2([P(texto_caracterizacion, sty_norm)]))

    # ═══════ MATRIZ AJUSTES — LANDSCAPE ═══════
    story.append(NextPageTemplate(['Landscape']))
    story.append(PageBreak())

    story.append(_banner("AJUSTES RAZONABLES"))
    story.append(Spacer(1, 6))

    WA = [3.5*cm, 4*cm, 3.8*cm, 3.8*cm, 6.6*cm, 4*cm]

    hdr_aj = [
        [P(u"\u00c1rea/asignatura/campo de pensamiento/\u00e1rea de desarrollo/dimensiones/articulaci\u00f3n con la educaci\u00f3n media/din\u00e1micas de la vida diaria/convivencia u otra seg\u00fan sea el caso", sty_ccw),
         P(u"Barreras identificadas en el contexto \u2014 Describir.", sty_ccw),
         P("Tipo de ajuste razonable \u2014 facilitador", sty_ccw),
         P("Apoyo requerido (Talento humano, t\u00e9cnico, tecnol\u00f3gico, comunicativo, otro)", sty_ccw),
         P(u"Descripci\u00f3n de tipo de ajustes y apoyos", sty_ccw),
         P("Seguimiento \u2014 En clave de temporalidad, responsable y medios.", sty_ccw)],
    ]
    # Subtitulos grises bajo headers
    hdr_sub = [
        ["", P("Actitudinales, tecnol\u00f3gicas, comunicativas, metodol\u00f3gicas, infraestructura, entre otras.", sty_cg),
         P("(Recursos o materiales, did\u00e1cticas o de estrategias, tiempo, metas de aprendizaje, estrategias de evaluaci\u00f3n, infraestructura)", sty_cg),
         P("(Talento humano, t\u00e9cnico, tecnol\u00f3gico, comunicativo, otro)", sty_cg),
         P("Si el ajuste se realiza en la meta de aprendizaje, escribir la nueva meta que corresponde para el actual per\u00edodo seg\u00fan el plan de estudios. Incluir la frecuencia del ajuste y del apoyo.", sty_cg),
         P("En clave de temporalidad, responsable y medios.", sty_cg)],
    ]

    ajustes = _ajustes_del_periodo_pdf(piar, periodo)
    areas_agrupadas = {}
    for aj in ajustes:
        areas_agrupadas.setdefault(aj.area, []).append(aj)

    def _fragmentar(texto, limite=480):
        """Divide celdas extensas para que ReportLab pueda paginar la matriz,
        conservando los saltos de línea explícitos del contenido."""
        bloques = [linea.strip() for linea in str(texto or "").split("\n")]
        bloques = [linea for linea in bloques if linea]
        if not bloques:
            return [""]

        fragmentos: list[str] = []
        actual = ""
        for bloque in bloques:
            piezas: list[str] = []
            palabras: list[str] = []
            longitud = 0
            for palabra in bloque.split():
                if palabras and longitud + len(palabra) + 1 > limite:
                    piezas.append(" ".join(palabras))
                    palabras, longitud = [], 0
                palabras.append(palabra)
                longitud += len(palabra) + 1
            if palabras:
                piezas.append(" ".join(palabras))

            for pieza in piezas:
                candidato = actual + "\n" + pieza if actual else pieza
                if len(candidato) > limite and actual:
                    fragmentos.append(actual)
                    actual = pieza
                else:
                    actual = candidato
        if actual:
            fragmentos.append(actual)
        return fragmentos or [""]

    aj_rows = [hdr_aj[0], hdr_sub[0]]
    area_idx = 0

    # La descripción de los ajustes se conserva en una sola celda por asignatura:
    # se reduce la fuente cuando es extensa para que la fila siga cabiendo en la página.
    max_desc = max((len(aj.ajustes_estrategias or "") for aj in ajustes), default=0)
    if max_desc > 6000:
        desc_font, desc_lead = 4.5, 5.5
    elif max_desc > 4000:
        desc_font, desc_lead = 5.0, 6.5
    elif max_desc > 2500:
        desc_font, desc_lead = 5.5, 7.0
    elif max_desc > 1200:
        desc_font, desc_lead = 6.5, 8.5
    else:
        desc_font, desc_lead = 7.5, 9.5
    sty_desc = ParagraphStyle('DescAjustes', parent=sty_c, fontSize=desc_font, leading=desc_lead)

    for area_name, aj_list in sorted(areas_agrupadas.items()):
        area_idx += 1
        for aj in aj_list:
            area_col = str(area_idx) + ". " + area_name
            titulo = (aj.titulo_tema or "") if hasattr(aj, 'titulo_tema') else ""
            objetivos = aj.objetivos_propositos or ""
            dba = (aj.dba_referencia or "") if hasattr(aj, 'dba_referencia') else ""
            if titulo: area_col += "\n" + titulo
            if objetivos: area_col += "\nObjetivos / Prop\u00f3sitos de Aprendizaje: " + objetivos
            if dba: area_col += "\nDBA: " + dba

            barr = aj.barreras_evidenciadas or ""
            tipo = aj.tipo_ajuste or ""
            apoyo = aj.apoyo_requerido or ""
            desc = aj.ajustes_estrategias or ""

            seg = ""
            eva = aj.evaluacion_ajustes or ""
            if eva: seg += u"Evaluaci\u00f3n: " + eva
            temp = aj.temporalidad or ""
            resp = aj.responsable or ""
            med = aj.medios_verificacion or ""
            if temp: seg += ("\n" if seg else "") + "Temporalidad: " + temp
            if resp: seg += ("\n" if seg else "") + "Responsable: " + resp
            if med: seg += ("\n" if seg else "") + "Medios: " + med
            if not seg: seg = "Pendiente"

            columnas = [
                _fragmentar(area_col), _fragmentar(barr), _fragmentar(tipo),
                _fragmentar(apoyo), [desc], _fragmentar(seg),
            ]
            estilos = [sty_c, sty_c, sty_c, sty_c, sty_desc, sty_c]
            for fragmento in range(max(len(columna) for columna in columnas)):
                aj_rows.append([
                    P(columna[fragmento] if fragmento < len(columna) else "", estilos[indice])
                    for indice, columna in enumerate(columnas)
                ])

    for cobertura in getattr(piar, "asignaturas_estado", None) or []:
        if cobertura.estado == "no_requiere":
            aj_rows.append([
                P(cobertura.nombre_asignatura, sty_c),
                P("No se identificaron barreras que requieran ajuste.", sty_c),
                P("No requiere ajuste razonable", sty_c),
                P("", sty_c),
                P(cobertura.justificacion or "", sty_desc),
                P("Cobertura académica resuelta", sty_c),
            ])

    t_aj = LongTable(aj_rows, colWidths=WA, repeatRows=2, splitByRow=1, splitInRow=1)
    t_aj.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('FONTSIZE', (0,1), (-1,1), 6.5),
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,1), gris_fondo),
        ('FONTNAME', (0,2), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,2), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_aj)

    # ═══════ Volver a portrait ═══════
    story.append(NextPageTemplate(['Portrait']))
    story.append(PageBreak())

    # ═══════ FIRMAS DOCENTES (bloques de 3 + apoyo) ═══════
    docentes_list = [
        (item.nombre, item.area or "")
        for item in participantes
        if item.rol_piar == "docente_aula"
    ]
    if not docentes_list:
        docentes_list = []
        for docente in [d.strip() for d in docentes_texto.split(",") if d.strip()]:
            if "(" in docente and ")" in docente:
                docentes_list.append((docente[:docente.rfind("(")].strip(), docente[docente.rfind("(")+1:docente.rfind(")")].strip()))
            else:
                docentes_list.append((docente, ""))

    firmas_por_docente = {}
    for nombre, area in docentes_list:
        nombre = " ".join(nombre.split())
        firma = firmas_por_docente.setdefault(
            nombre.casefold(), {"nombre": nombre, "areas": {}}
        )
        area = " ".join(area.split())
        if area:
            firma["areas"].setdefault(area.casefold(), area)
    docentes_list = [
        (firma["nombre"], ", ".join(firma["areas"].values()))
        for firma in firmas_por_docente.values()
    ]

    for block_num in range(max(3, (len(docentes_list) + 2) // 3)):
        rows = []
        rows.append([P("Nombre docente", sty_cc), P("Nombre docente", sty_cc), P("Nombre docente", sty_cc)])
        rows.append([P("", sty_cc), P("", sty_cc), P("", sty_cc)])
        rows.append([P(u"\u00c1rea", sty_cc), P(u"\u00c1rea", sty_cc), P(u"\u00c1rea", sty_cc)])
        rows.append([P("", sty_cc), P("", sty_cc), P("", sty_cc)])
        rows.append([P("Firma", sty_cc), P("Firma", sty_cc), P("Firma", sty_cc)])
        rows.append([P("", sty_cc), P("", sty_cc), P("", sty_cc)])
        for i in range(3):
            idx = block_num * 3 + i
            if idx < len(docentes_list):
                nom, area = docentes_list[idx]
                rows[1][i] = P(nom, sty_cc)
                rows[3][i] = P(area, sty_cc)
        if block_num > 0: story.append(Spacer(1, 6))
        t = Table(rows, colWidths=[5.5*cm, 5.5*cm, 5.5*cm], splitByRow=0, rowHeights=[None, None, None, None, None, 2*cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), gris_label),
            ('BACKGROUND', (0,2), (-1,2), gris_label),
            ('BACKGROUND', (0,4), (-1,4), gris_label),
            ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)

    # Bloque apoyo
    story.append(Spacer(1, 6))
    apoyo_rows = [
        [P("Nombre docente orientador", sty_cc), P(u"Nombre docente de apoyo pedag\u00f3gico", sty_cc), P(u"Nombre coordinador pedag\u00f3gico", sty_cc)],
        [P("", sty_cc), P("", sty_cc), P("", sty_cc)],
        [P(u"\u00c1rea", sty_cc), P(u"\u00c1rea", sty_cc), P(u"\u00c1rea", sty_cc)],
        [P("", sty_cc), P("", sty_cc), P("", sty_cc)],
        [P("Firma", sty_cc), P("Firma", sty_cc), P("Firma", sty_cc)],
        [P("", sty_cc), P("", sty_cc), P("", sty_cc)],
    ]
    t_apoyo = Table(apoyo_rows, colWidths=[5.5*cm, 5.5*cm, 5.5*cm], rowHeights=[None, None, None, None, None, 2*cm])
    t_apoyo.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), gris_label),
        ('BACKGROUND', (0,2), (-1,2), gris_label),
        ('BACKGROUND', (0,4), (-1,4), gris_label),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_apoyo)
    story.append(Spacer(1, 6))

    # ═══════ ACTA DE ACUERDO ═══════
    story.append(PageBreak())
    story.append(_banner("ACTA DE ACUERDO"))
    story.append(Spacer(1, 6))

    acta_hdr_data = [
        [_label_cell("Fecha y Lugar de Diligenciamiento"), P(
            f"{acta.fecha_firma.strftime('%d/%m/%Y') if (acta and acta.fecha_firma) else 'DD/MM/AAAA'}  {direccion_institucion}", sty_c)],
        [_label_cell("Nombre y rol de la Persona que diligencia"), P(primer_docente, sty_c)],
        [_label_cell(u"Instituci\u00f3n Educativa"), P(inst_nombre, sty_c)],
        [_label_cell("Sede"), P(sede_nombre, sty_c)],
    ]
    acta_top_rows = []
    for label, val in acta_hdr_data:
        acta_top_rows.append([P(label['text'].text, sty_cb), val])
    t_acta_top = Table(acta_top_rows, colWidths=[7*cm, 9.2*cm])
    t_acta_top.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,-1), gris_label),
        ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.black),
        ('LINEAFTER', (0,0), (0,-1), 0.5, colors.black),
    ]))
    story.append(t_acta_top)
    story.append(Spacer(1, 6))

    id_data = [
        [P("Nombre", sty_cb), P(f"{estudiante.nombres} {estudiante.apellidos}", sty_c),
         P("Edad", sty_cb), P(f"{edad if edad is not None else ''}", sty_c),
         P("Grado", sty_cb), P(grado_nombre, sty_c)],
    ]
    story.append(_table(id_data, [3*cm, 4*cm, 2*cm, 2*cm, 2*cm, 3*cm],
        [('BACKGROUND', (0,0), (0,0), gris_label), ('BACKGROUND', (2,0), (2,0), gris_label), ('BACKGROUND', (4,0), (4,0), gris_label)]))
    story.append(Spacer(1, 8))

    def _celda_acta(contenido):
        tabla = Table([[contenido]], colWidths=[16.2*cm])
        tabla.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        return tabla

    story.append(_celda_acta([
        P(u"Seg\u00fan el Decreto 1421 de 2017 la educaci\u00f3n inclusiva es un proceso permanente que reconoce, valora y responde a la diversidad de caracter\u00edsticas, intereses, posibilidades y expectativas de los estudiantes para promover su desarrollo, aprendizaje y participaci\u00f3n, en un ambiente de aprendizaje com\u00fan, sin discriminaci\u00f3n o exclusi\u00f3n.", sty_norm),
        P("La inclusi\u00f3n solo es posible cuando se unen los esfuerzos del colegio, el estudiante, docentes, directivos docentes y familias. De ah\u00ed la importancia de formalizar con las firmas, la presente Acta de Acuerdo.", sty_norm),
        P("El Establecimiento Educativo ha realizado la valoraci\u00f3n pedag\u00f3gica y definido los ajustes razonables que facilitar\u00e1n al estudiante su proceso.", sty_norm),
        P("La Familia se compromete a cumplir y firmar los compromisos se\u00f1alados en el PIAR y en las actas de acuerdo, para fortalecer los procesos escolares del estudiante y en particular a:", sty_norm),
    ]))
    story.append(Spacer(1, 6))

    comp_intro = "Incluya aqu\u00ed los compromisos espec\u00edficos para implementar en el aula que requieran ampliaci\u00f3n o detalle adicional al incluido en el PIAR."
    contenido_comp = [P(comp_intro, sty_norm)]
    if acta and acta.compromisos_aula and acta.compromisos_aula.strip():
        contenido_comp.append(Spacer(1, 4))
        contenido_comp.append(P(acta.compromisos_aula, sty_norm))
    t_comp = _celda_acta(contenido_comp)
    story.append(t_comp)
    story.append(Spacer(1, 6))

    t_casa = _celda_acta([P("Y en casa apoyar\u00e1 con las siguientes actividades:", sty_norm)])
    story.append(t_casa)
    story.append(Spacer(1, 4))
    act_cols = [5*cm, 7*cm, 5*cm]
    act_hdr = [
        [P("Nombre de la Actividad", sty_cc), P(u"Descripci\u00f3n de la estrategia", sty_cc),
         P("Frecuencia: D Diaria, S Semanal, P Permanente\nD __ S__ P__", sty_cc)]
    ]
    if acta and acta.compromisos_casa:
        for c in acta.compromisos_casa:
            act_hdr.append([P(c.nombre_actividad or "", sty_c), P(c.descripcion_estrategia or "", sty_c), P(c.frecuencia or "", sty_c)])
    story.append(_table(act_hdr, act_cols, [('BACKGROUND', (0,0), (-1,0), gris_label)]))
    story.append(Spacer(1, 12))

    story.append(P("Firma de los Actores comprometidos:", sty_sec))
    firma_data = [
        [P("Estudiante", sty_cc), P("Acudiente / familia", sty_cc)],
        [P("", sty_c), P("", sty_c)],
        [P("Docentes", sty_cc), P("Docentes", sty_cc)],
        [P("", sty_c), P("", sty_c)],
        [P("Directivo docente", sty_cc), P("Directivo docente", sty_cc)],
        [P("", sty_c), P("", sty_c)],
    ]
    t_firmas = Table(firma_data, colWidths=[8*cm, 8*cm])
    t_firmas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), gris_label), ('BACKGROUND', (1,0), (1,0), gris_label),
        ('BACKGROUND', (0,2), (0,2), gris_label), ('BACKGROUND', (1,2), (1,2), gris_label),
        ('BACKGROUND', (0,4), (0,4), gris_label), ('BACKGROUND', (1,4), (1,4), gris_label),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('MINROWHEIGHT', (0,1), (-1,1), 40), ('MINROWHEIGHT', (0,3), (-1,3), 40),
        ('MINROWHEIGHT', (0,5), (-1,5), 40),
    ]))
    story.append(t_firmas)

    # ═══════ EVIDENCIAS ═══════
    evidencias = []
    for ajuste in _ajustes_del_periodo_pdf(piar, periodo):
        for evidencia in (getattr(ajuste, "evidencias", None) or []):
            evidencias.append((ajuste, evidencia))
    evidencias.sort(key=lambda par: (
        (par[0].area or "").casefold(),
        str(getattr(par[1], "fecha", "") or ""),
        str(getattr(par[1], "fecha_subida", "") or ""),
    ))

    if evidencias:
        ancho_landscape = ls_size[0] - 3*cm
        story.append(NextPageTemplate(['Landscape']))
        story.append(PageBreak())
        story.append(_banner("EVIDENCIAS", ancho=ancho_landscape))
        story.append(Spacer(1, 8))

        filas_evidencia = [[
            P("Asignatura - Docente", sty_cb),
            P("Descripci\u00f3n y fecha", sty_cb),
            P("Evidencia", sty_cb),
        ]]
        for ajuste, evidencia in evidencias:
            docente = "\u2014"
            creador = getattr(evidencia, "creador", None)
            if creador is not None:
                nombre_docente = " ".join(
                    parte for parte in (
                        getattr(creador, "nombre", ""), getattr(creador, "apellido", "")
                    ) if parte
                ).strip()
                if nombre_docente:
                    docente = nombre_docente

            fecha_evidencia = getattr(evidencia, "fecha", None)
            fecha_str = fecha_evidencia.strftime("%d/%m/%Y") if fecha_evidencia else "\u2014"

            imagen_evidencia = _imagen_evidencia_para_pdf(
                getattr(evidencia, "ruta_archivo", None), caja=(310.0, 240.0)
            )
            if imagen_evidencia is not None:
                celda_evidencia = imagen_evidencia
            elif getattr(evidencia, "tipo_archivo", "imagen") == "pdf":
                celda_evidencia = P(
                    f"Documento PDF: {getattr(evidencia, 'nombre_archivo', '')}", sty_c
                )
            else:
                celda_evidencia = P("Imagen no disponible", sty_c)

            filas_evidencia.append([
                P(f"{(ajuste.area or '').strip()}\n{docente}", sty_c),
                P(f"{(getattr(evidencia, 'descripcion', '') or '').strip()}\n{fecha_str}", sty_c),
                celda_evidencia,
            ])

        ancho_asignatura, ancho_descripcion = 170.0, 210.0
        t_evidencias = LongTable(
            filas_evidencia,
            colWidths=[ancho_asignatura, ancho_descripcion, ancho_landscape - ancho_asignatura - ancho_descripcion],
            repeatRows=1,
        )
        t_evidencias.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), gris_label),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_evidencias)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
