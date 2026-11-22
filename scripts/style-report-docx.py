"""Apply the report PDF's CSS-equivalent formatting to an editable DOCX."""

from pathlib import Path
import sys

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor


BODY_FONT = "Times New Roman"
CODE_FONT = "Consolas"
BODY_SIZE = Pt(11)
CODE_SIZE = Pt(9.5)
LINK_COLOR = RGBColor(0x06, 0x45, 0xAD)


def find_style(styles, name):
    target = name.replace(" ", "").lower()
    for style in styles:
        if style.name == name or style.style_id.replace(" ", "").lower() == target:
            return style
    return None


def set_font(style, name, size=None, bold=None, color=None):
    style.font.name = name
    if size is not None:
        style.font.size = size
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    style.element.rPr.rFonts.set(qn("w:ascii"), name)
    style.element.rPr.rFonts.set(qn("w:hAnsi"), name)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), name)


def set_cell_margins(cell, top=60, start=90, bottom=60, end=90):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in {
        "top": top,
        "start": start,
        "bottom": bottom,
        "end": end,
    }.items():
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_row_pagination(row, repeat_header=False):
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))
    if repeat_header and tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def style_document(input_path: Path, output_path: Path):
    document = Document(input_path)
    styles = document.styles

    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(22)
        section.right_margin = Mm(20)
        section.bottom_margin = Mm(22)
        section.left_margin = Mm(25)
        section.header_distance = Mm(10)
        section.footer_distance = Mm(10)

        # The PDF intentionally has no generated browser header/footer.
        for part in (section.header, section.footer):
            for paragraph in part.paragraphs:
                paragraph.clear()

    normal = find_style(styles, "Normal")
    set_font(normal, BODY_FONT, BODY_SIZE)
    normal.paragraph_format.line_spacing = 1.45
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True

    body_text = find_style(styles, "Body Text")
    if body_text is not None:
        set_font(body_text, BODY_FONT, BODY_SIZE)
        body_text.paragraph_format.line_spacing = 1.45
        body_text.paragraph_format.space_after = Pt(6)

    heading_specs = {
        "Title": (Pt(24), False, Pt(12), WD_ALIGN_PARAGRAPH.CENTER),
        "Subtitle": (Pt(14), False, Pt(6), WD_ALIGN_PARAGRAPH.CENTER),
        "Author": (Pt(12), False, Pt(3), WD_ALIGN_PARAGRAPH.CENTER),
        "Date": (Pt(11), False, Pt(12), WD_ALIGN_PARAGRAPH.CENTER),
        "Heading 1": (Pt(20), True, Pt(8), WD_ALIGN_PARAGRAPH.LEFT),
        "Heading 2": (Pt(14), False, Pt(6), WD_ALIGN_PARAGRAPH.LEFT),
        "Heading 3": (Pt(12), False, Pt(4), WD_ALIGN_PARAGRAPH.LEFT),
        "TOC Heading": (Pt(14), False, Pt(8), WD_ALIGN_PARAGRAPH.LEFT),
    }
    for name, (size, page_break, after, alignment) in heading_specs.items():
        style = find_style(styles, name)
        if style is None:
            continue
        set_font(style, BODY_FONT, size, bold=True)
        style.paragraph_format.page_break_before = page_break
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = (
            Pt(19.6) if name == "Heading 2" else Pt(10)
        )
        style.paragraph_format.space_after = after
        style.paragraph_format.alignment = alignment

    for name in ("Source Code", "Verbatim Char", "Code Block"):
        style = find_style(styles, name)
        if style is not None:
            set_font(style, CODE_FONT, CODE_SIZE)

    hyperlink = find_style(styles, "Hyperlink")
    if hyperlink is not None:
        set_font(hyperlink, BODY_FONT, BODY_SIZE, color=LINK_COLOR)
        hyperlink.font.underline = False

    for name in ("TOC 1", "TOC 2", "TOC 3"):
        style = find_style(styles, name)
        if style is not None:
            set_font(style, BODY_FONT, BODY_SIZE)
            style.paragraph_format.line_spacing = 1.15
            style.paragraph_format.space_after = Pt(2)

    # Normalize explicit run formatting emitted by Pandoc while preserving
    # heading, title, hyperlink, and inline-code sizing.
    for paragraph in document.paragraphs:
        paragraph_style = paragraph.style.name if paragraph.style else "Normal"
        if paragraph.text.strip() == "Final Submission Checklist":
            paragraph.paragraph_format.page_break_before = True
        for run in paragraph.runs:
            run_style = run.style.name if run.style else ""
            if run_style == "Verbatim Char":
                font_name, font_size = CODE_FONT, CODE_SIZE
            elif paragraph_style == "Code Block":
                font_name, font_size = CODE_FONT, CODE_SIZE
            elif paragraph_style in heading_specs:
                font_name, font_size = BODY_FONT, heading_specs[paragraph_style][0]
            else:
                font_name, font_size = BODY_FONT, BODY_SIZE
            run.font.name = font_name
            run.font.size = font_size
            run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), font_name)
            run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), font_name)
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font_name)

    for table in document.tables:
        table_grid = find_style(styles, "Table Grid")
        if table_grid is not None:
            table.style = table_grid
        table.autofit = True
        for row_index, row in enumerate(table.rows):
            set_row_pagination(row, repeat_header=row_index == 0)
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                set_cell_margins(cell)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = 1.15
                    paragraph.paragraph_format.space_after = Pt(2)
                    for run in paragraph.runs:
                        is_code = run.style and run.style.name == "Verbatim Char"
                        run.font.name = CODE_FONT if is_code else BODY_FONT
                        run.font.size = CODE_SIZE if is_code else BODY_SIZE
                        run._element.get_or_add_rPr().rFonts.set(
                            qn("w:eastAsia"), CODE_FONT if is_code else BODY_FONT
                        )
                        if row_index == 0:
                            run.font.bold = True

    document.core_properties.title = (
        "SafeTrade: Smart-Contract Escrow with Delivery and Review Deadlines"
    )
    document.core_properties.author = "YUE Pu (20944719)"
    document.save(output_path)


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("report/report.docx")
    destination = Path(sys.argv[2]) if len(sys.argv) > 2 else source
    style_document(source, destination)
