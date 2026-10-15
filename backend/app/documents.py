import base64
import html
import io
import re
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .confia_product_catalog import ProductLine
from .storage import DOSSIER_TEMPLATE_PATH, LOGO_PATH

REGULATORY_FIELDS = (
    "registry_number",
    "classification",
    "calibration_certificate",
    "good_practices_certificate",
    "informed_consent_template",
)

# Paleta corporativa (AGENTS.md).
INK = "#071C21"
TEAL = "#0E2E33"
CREAM = "#F4EFE6"
AMBER = "#D97706"
GRID = "#D9D2C5"

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_BULLET = re.compile(r"^[-*]\s+(.*)$")
_NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
_RULE = re.compile(r"^(-{3,}|\*{3,})$")
_TABLE_SEPARATOR = re.compile(r":?-{3,}:?")
_IMAGE = re.compile(r"^!\[[^\]]*\]\(data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)\)$")


class DocumentRenderError(RuntimeError):
    """Se lanza cuando falta un recurso o ReportLab no puede compilar el PDF."""


def load_template() -> str:
    try:
        return DOSSIER_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise DocumentRenderError(f"No existe la plantilla: {DOSSIER_TEMPLATE_PATH}") from error


def _logo_markdown() -> str:
    # Sin logo no fallamos: el documento sale sin encabezado gráfico.
    if not LOGO_PATH.is_file():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"![ConfIA](data:image/png;base64,{encoded})"


def _fill(text: str, values: dict[str, str]) -> str:
    # Reemplazo literal de marcadores conocidos; no usamos str.format para que
    # llaves dentro del texto generado por el LLM no rompan el documento.
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _placeholder(key: str) -> str:
    return "{{" + key + "}}"


def build_dossier_prompt(prospect: dict, product: ProductLine) -> str:
    markers = ", ".join(_placeholder(field) for field in REGULATORY_FIELDS)
    official = product.regulatory.model_dump()
    official_lines = "\n".join(
        f"- {field} ({_placeholder(field)}): {official[field]}" for field in REGULATORY_FIELDS
    )
    return f"""
Redacta el cuerpo de un dossier regulatorio en Markdown enriquecido para revisión humana.
Usa tablas, viñetas y secciones con encabezados ## para: resumen ejecutivo, perfil del
prospecto, propuesta de valor del modelo Ozone-as-a-Service, consideraciones regulatorias
y próximos pasos.

Producto ofrecido: {product.name}

Datos regulatorios oficiales de ConfIA (catálogo maestro, solo lectura). Úsalos como única
fuente regulatoria:
{official_lines}

Reglas obligatorias:
- Para cualquier Registro Sanitario, clasificación o certificado escribe EXACTAMENTE el
  marcador correspondiente, sin cambiarlo ni completarlo: {markers}.
  El sistema reemplazará cada marcador por el valor oficial.
- No inventes números de registro, precios, concentraciones, certificados ni cifras clínicas.
- No afirmes propiedades terapéuticas sin cita explícita de la Declaración de Madrid.
- No incluyas la sección de datos regulatorios validados: la plantilla la añade.
- No escribas un título de nivel 1 (#); usa ## como encabezado más alto.

Datos del prospecto (la clínica; no son datos regulatorios):
{prospect}

Devuelve solo el Markdown del cuerpo, sin bloques de código que lo envuelvan.
"""


def render_dossier_markdown(
    body: str,
    lead_name: str,
    regulatory: dict[str, str],
) -> str:
    """Inserta el cuerpo generado y los datos validados en la plantilla.

    Los datos regulatorios se inyectan siempre desde `regulatory`, nunca desde el LLM.
    """
    body = _fill(body, regulatory)
    template = load_template()
    document = _fill(
        template,
        {
            "logo": _logo_markdown(),
            "lead_name": lead_name,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            **regulatory,
            "content": body,
        },
    )

    # Guardarraíl: si la plantilla perdió algún marcador regulatorio, el dossier no se emite.
    missing = [field for field in REGULATORY_FIELDS if _placeholder(field) not in template]
    if missing:
        raise DocumentRenderError(
            f"La plantilla no contiene los marcadores regulatorios: {', '.join(missing)}."
        )
    return document


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    body = ParagraphStyle("body", parent=base, fontName="Helvetica", fontSize=10.5, leading=15,
                          textColor=colors.HexColor(INK), spaceAfter=6)
    return {
        "body": body,
        "h1": ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=22,
                             textColor=colors.HexColor(TEAL), spaceBefore=6, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                             textColor=colors.HexColor(TEAL), spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                             textColor=colors.HexColor(TEAL), spaceBefore=8, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=16, bulletIndent=4),
        "quote": ParagraphStyle("quote", parent=body, leftIndent=8, backColor=colors.HexColor(CREAM),
                                borderPadding=6),
        "cell": ParagraphStyle("cell", parent=body, fontSize=9, leading=12, spaceAfter=0),
        "cell_head": ParagraphStyle("cell_head", parent=body, fontName="Helvetica-Bold", fontSize=9,
                                    leading=12, spaceAfter=0, textColor=colors.HexColor(CREAM)),
    }


def _inline(text: str) -> str:
    """Convierte negrita/cursiva de Markdown a las etiquetas de Paragraph, escapando HTML."""
    escaped = html.escape(text, quote=False)
    escaped = _BOLD.sub(r"<b>\1</b>", escaped)
    return _ITALIC.sub(r"<i>\1</i>", escaped)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(rows: list[str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    header = _cells(rows[0])
    body = [
        _cells(row)
        for row in rows[1:]
        if not all(_TABLE_SEPARATOR.fullmatch(cell) for cell in _cells(row))
    ]
    columns = len(header)
    data = [[Paragraph(_inline(cell), styles["cell_head"]) for cell in header]]
    for row in body:
        padded = (row + [""] * columns)[:columns]
        data.append([Paragraph(_inline(cell), styles["cell"]) for cell in padded])

    table = Table(data, colWidths=[width / columns] * columns, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TEAL)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(GRID)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _image(encoded: str) -> Image:
    data = base64.b64decode(encoded)
    image_width, image_height = ImageReader(io.BytesIO(data)).getSize()
    width = 4 * cm
    return Image(io.BytesIO(data), width=width, height=width * image_height / image_width)


def _markdown_flowables(text: str, styles: dict[str, ParagraphStyle], width: float) -> list:
    flowables: list = []
    pending: list[str] = []

    def flush_paragraph() -> None:
        if pending:
            flowables.append(Paragraph("<br/>".join(_inline(line) for line in pending), styles["body"]))
            pending.clear()

    lines = [line.strip() for line in text.splitlines()]
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1

        if not line:
            flush_paragraph()
            continue

        if line.startswith("|"):
            flush_paragraph()
            rows = [line]
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(lines[index])
                index += 1
            flowables.append(_table(rows, styles, width))
            flowables.append(Spacer(1, 6))
            continue

        image = _IMAGE.match(line)
        if image:
            flush_paragraph()
            flowables.append(_image(image.group(1)))
            continue

        if _RULE.match(line):
            flush_paragraph()
            flowables.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor(GRID),
                                        spaceBefore=6, spaceAfter=6))
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            level = {1: "h1", 2: "h2", 3: "h3"}[len(heading.group(1))]
            flowables.append(Paragraph(_inline(heading.group(2)), styles[level]))
            continue

        bullet = _BULLET.match(line)
        if bullet:
            flush_paragraph()
            flowables.append(Paragraph(_inline(bullet.group(1)), styles["bullet"], bulletText="•"))
            continue

        numbered = _NUMBERED.match(line)
        if numbered:
            flush_paragraph()
            flowables.append(Paragraph(_inline(numbered.group(2)), styles["bullet"],
                                       bulletText=f"{numbered.group(1)}."))
            continue

        if line.startswith(">"):
            flush_paragraph()
            flowables.append(Paragraph(_inline(line[1:].strip()), styles["quote"]))
            continue

        pending.append(line)

    flush_paragraph()
    return flowables


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor(TEAL))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"ConfIA · Página {document.page}")
    canvas.restoreState()


def render_pdf(document_markdown: str) -> bytes:
    """Compila el Markdown del dossier en PDF con ReportLab (Python puro, sin librerías nativas)."""
    margin = 2 * cm
    width = A4[0] - 2 * margin
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title="Dossier regulatorio ConfIA",
        author="ConfIA",
    )
    try:
        story = _markdown_flowables(document_markdown, _styles(), width)
        document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    except Exception as error:
        raise DocumentRenderError(f"No se pudo compilar el PDF: {error}") from error
    return buffer.getvalue()
