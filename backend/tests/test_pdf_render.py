from app.confia_product_catalog import PRODUCT_LINES
from app.documents import render_dossier_markdown, render_pdf

# PNG 1x1 válido, para probar la ruta de imágenes sin depender de logo_confia.png.
TINY_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

SAMPLE = f"""![ConfIA](data:image/png;base64,{TINY_PNG})

# Dossier regulatorio: Clínica Demo

**Generado:** 2026-10-15 · **Estado:** borrador

---

## Resumen ejecutivo
Texto con **negrita**, *cursiva* y caracteres especiales: <script>alert(1)</script> & más.
Segunda línea del mismo párrafo.

- Viñeta uno con **énfasis**
- Viñeta dos

1. Paso numerado uno
2. Paso numerado dos

> Nota de advertencia para revisión humana.

| Campo | Valor |
|---|---|
| Registro Sanitario DIGEMID | DM-14820-E |
| Certificado | Calibración de fábrica — SEDECAL ISO 13485 |
| Fila incompleta |
"""


def test_renders_a_valid_pdf_with_markdown_features():
    pdf = render_pdf(SAMPLE)

    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert len(pdf) > 2000


def test_escapes_html_in_user_content():
    # El texto generado por el LLM nunca debe interpretarse como markup de ReportLab.
    pdf = render_pdf("## Título\n\nTexto con <b>tags</b> y & sin cerrar **negrita")

    assert pdf.startswith(b"%PDF-")


def test_empty_markdown_still_produces_a_pdf():
    assert render_pdf("").startswith(b"%PDF-")


def test_full_dossier_pipeline_renders_with_catalog_data():
    line = PRODUCT_LINES["ozonobaric_ahtm"]
    body = "## Resumen\n\nEl equipo {{registry_number}} cumple con **{{classification}}**."

    document = render_dossier_markdown(body, "Clínica Demo", line.regulatory.model_dump())
    pdf = render_pdf(document)

    assert pdf.startswith(b"%PDF-")
    assert "{{" not in document
