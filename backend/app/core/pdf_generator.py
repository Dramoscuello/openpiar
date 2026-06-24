# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import io
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.adapters.db.models import PiarORM, ConfiguracionSistemaORM


def generate_acta_pdf(piar: PiarORM, config: Optional[ConfiguracionSistemaORM]) -> bytes:
    """
    Genera el archivo PDF del Acta de Acuerdo (Anexo 3) de un PIAR.
    Retorna los bytes del PDF.
    """
    buffer = io.BytesIO()
    
    # Configuración de página con márgenes de 0.75 pulgadas (54 pt)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    # Paleta de Colores
    primary_color = colors.HexColor("#1A365D")  # Deep Blue
    secondary_color = colors.HexColor("#4A5568") # Slate Grey
    border_color = colors.HexColor("#CBD5E1")    # Light Grey
    bg_light = colors.HexColor("#F8FAFC")        # Soft Blue/Grey
    
    # Estilos
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=6,
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=15,
        alignment=1 # Center
    )
    
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBodyTextCustom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        fontSize=9,
        leading=11
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=9,
        leading=12
    )

    table_cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=primary_color
    )

    story = []
    
    # 1. ENCABEZADO
    inst_nombre = config.nombre_institucion if config else "INSTITUCIÓN EDUCATIVA DE PRUEBA"
    rector_nombre = config.nombre_rector if config else "No especificado"
    dane_codigo = config.codigo_dane if config else "No especificado"
    nit_codigo = config.nit if config else "No especificado"
    
    story.append(Paragraph(inst_nombre.upper(), title_style))
    story.append(Paragraph("ANEXO 3: ACTA DE ACUERDO Y CORRESPONSABILIDAD FAMILIAR", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. INFORMACIÓN GENERAL DEL ESTUDIANTE Y LA IE
    estudiante = piar.estudiante
    fecha_firma_str = "No firmada"
    compromisos_aula = "No se han especificado compromisos específicos en el aula."
    
    acta = piar.acta_acuerdo
    if acta and acta.fecha_firma:
        fecha_firma_str = acta.fecha_firma.strftime("%d/%m/%Y")
    if acta and acta.compromisos_aula:
        compromisos_aula = acta.compromisos_aula

    general_info_data = [
        [
            Paragraph("Estudiante:", table_cell_bold_style),
            Paragraph(f"{estudiante.nombres} {estudiante.apellidos}", table_cell_style),
            Paragraph("Documento:", table_cell_bold_style),
            Paragraph(f"{estudiante.tipo_documento} {estudiante.numero_documento}", table_cell_style)
        ],
        [
            Paragraph("Edad / Grado:", table_cell_bold_style),
            Paragraph(f"{estudiante.edad} años / Grado {estudiante.grupo_id or 'No asignado'}", table_cell_style),
            Paragraph("Fecha Firma Acta:", table_cell_bold_style),
            Paragraph(fecha_firma_str, table_cell_style)
        ],
        [
            Paragraph("Rector(a):", table_cell_bold_style),
            Paragraph(rector_nombre, table_cell_style),
            Paragraph("NIT / Código DANE:", table_cell_bold_style),
            Paragraph(f"NIT: {nit_codigo} / DANE: {dane_codigo}", table_cell_style)
        ]
    ]
    
    # Ancho total: 504 pt (Letter es 612 x 792. Con 54 pt de margen izq/der queda 504 pt de ancho útil)
    info_table = Table(general_info_data, colWidths=[80, 172, 85, 167])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # 3. COMPROMISOS DEL ESTABLECIMIENTO EDUCATIVO (AULA)
    story.append(Paragraph("1. Compromisos del Establecimiento Educativo (Aula)", h2_style))
    intro_colegio = (
        "La institución educativa se compromete a brindar acompañamiento pedagógico continuo, "
        "flexibilizar las evaluaciones pertinentes y aplicar las adaptaciones curriculares descritas "
        "en la Matriz de Ajustes Razonables (Anexo 2) del estudiante. Específicamente, en el aula se acuerda:"
    )
    story.append(Paragraph(intro_colegio, body_style))
    story.append(Spacer(1, 6))
    
    # Caja para los compromisos del aula
    aula_box_data = [[Paragraph(compromisos_aula, body_style)]]
    aula_table = Table(aula_box_data, colWidths=[504])
    aula_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(aula_table)
    story.append(Spacer(1, 15))
    
    # 4. COMPROMISOS DE LA FAMILIA (CASA)
    story.append(Paragraph("2. Compromisos de Apoyo Familiar en Casa", h2_style))
    intro_familia = (
        "La familia del estudiante se compromete a realizar el acompañamiento correspondiente en el hogar, "
        "asistir a las convocatorias de la institución y colaborar en el desarrollo de las actividades planificadas. "
        "A continuación se detallan las estrategias acordadas para implementar en casa:"
    )
    story.append(Paragraph(intro_familia, body_style))
    story.append(Spacer(1, 8))
    
    # Tabla de compromisos de casa
    compromisos_list = acta.compromisos_casa if (acta and acta.compromisos_casa) else []
    
    if len(compromisos_list) == 0:
        story.append(Paragraph("<i>No se han registrado actividades de apoyo familiar específicas para este periodo.</i>", body_style))
    else:
        casa_table_data = [
            [
                Paragraph("Actividad", table_header_style),
                Paragraph("Estrategia / Descripción", table_header_style),
                Paragraph("Frecuencia", table_header_style)
            ]
        ]
        
        for c in compromisos_list:
            frecuencia_es = c.frecuencia.capitalize()
            casa_table_data.append([
                Paragraph(c.nombre_actividad, table_cell_bold_style),
                Paragraph(c.descripcion_estrategia, table_cell_style),
                Paragraph(frecuencia_es, table_cell_style)
            ])
            
        casa_table = Table(casa_table_data, colWidths=[120, 284, 100])
        casa_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(casa_table)
        
    story.append(Spacer(1, 20))
    
    # 5. FIRMAS Y CORRESPONSABILIDAD (Mantenemos todo junto en bloque para evitar firmas huérfanas)
    firmas = []
    
    intro_firmas = (
        "En constancia de acuerdo sobre el presente Plan Individual de Ajustes Razonables (PIAR) "
        "y sus compromisos correspondientes, firman los actores involucrados en el proceso educativo:"
    )
    firmas.append(Paragraph(intro_firmas, body_style))
    firmas.append(Spacer(1, 15))
    
    # Helper para formatear estado de firma
    def status_firma(firmado: bool) -> str:
        return "✓ FIRMADO DIGITALMENTE" if firmado else "PENDIENTE DE FIRMA"
        
    f_estudiante = acta.firmado_estudiante if acta else False
    f_acudiente = acta.firmado_acudiente if acta else False
    f_docente_apoyo = acta.firmado_docente_apoyo if acta else False
    f_docentes_aula = acta.firmado_docentes_aula if acta else False
    f_directivo = acta.firmado_directivo if acta else False
    
    docentes_nombres = piar.docentes_elaboran if piar.docentes_elaboran else "Docentes de Aula"

    firmas_layout_data = [
        [
            Paragraph("<b>Firma del Estudiante</b><br/><br/>________________________<br/>" + status_firma(f_estudiante), table_cell_style),
            Paragraph("<b>Firma del Acudiente / Familia</b><br/><br/>________________________<br/>" + status_firma(f_acudiente), table_cell_style)
        ],
        [
            Paragraph("<b>Firma Docente de Apoyo</b><br/><br/>________________________<br/>" + status_firma(f_docente_apoyo), table_cell_style),
            Paragraph(f"<b>Docentes de Aula</b><br/><br/>________________________<br/>{docentes_nombres}<br/>" + status_firma(f_docentes_aula), table_cell_style)
        ],
        [
            Paragraph(f"<b>Directivo Docente</b><br/><br/>________________________<br/>{rector_nombre} (Rector/a)<br/>" + status_firma(f_directivo), table_cell_style),
            Paragraph("", table_cell_style) # Espacio vacío para alinear
        ]
    ]
    
    firmas_table = Table(firmas_layout_data, colWidths=[252, 252])
    firmas_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    firmas.append(firmas_table)
    
    story.append(KeepTogether(firmas))
    
    # Construir PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
