#!/usr/bin/env python3
"""
A.R.G.U.S. — Technical Development Documentation Generator (.docx)
Milestones 7 & 8: Security, Application/OOP & IoT Integration
Reads and converts docs/ARGUS_TODAY_DEVELOPMENT_DOCUMENTATION_M7_M8.md into a
professionally formatted Microsoft Word (.docx) document.
"""

import os
import re
import sys
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MD_PATH = WORKSPACE_ROOT / "docs" / "ARGUS_TODAY_DEVELOPMENT_DOCUMENTATION_M7_M8.md"
DOCX_PATH = WORKSPACE_ROOT / "docs" / "ARGUS_TODAY_DEVELOPMENT_DOCUMENTATION_M7_M8.docx"

# Color Palette
NAVY = RGBColor(26, 54, 93)       # #1A365D - Heading 1 & Main Title
BLUE = RGBColor(43, 108, 176)     # #2B6CB0 - Heading 2
TEAL = RGBColor(49, 151, 149)     # #319795 - Heading 3
CHARCOAL = RGBColor(45, 55, 72)   # #2D3748 - Body text
MUTED = RGBColor(113, 128, 150)   # #718096 - Captions & Subtitles
CODE_COLOR = RGBColor(30, 41, 59) # #1E293B
WHITE = RGBColor(255, 255, 255)

HEX_NAVY = "1A365D"
HEX_LIGHT_BG = "F7FAFC"
HEX_BORDER = "CBD5E0"
HEX_CALLOUT_BG = "EDF2F7"
HEX_CALLOUT_BORDER = "3182CE"
HEX_CODE_BG = "F1F5F9"


def set_cell_background(cell, fill_hex):
    """Sets background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding in twentieths of a point (dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def add_callout(doc, text, title="CRITICAL NOTICE / DISCLOSURE"):
    """Adds a callout box with a colored left border and subtle background."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, HEX_CALLOUT_BG)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=160)
    
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="36" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    run_title = p.add_run(f"■ {title.upper()}\n")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(9.5)
    run_title.font.bold = True
    run_title.font.color.rgb = BLUE
    
    run_body = p.add_run(text)
    run_body.font.name = "Arial"
    run_body.font.size = Pt(9)
    run_body.font.color.rgb = CHARCOAL
    
    # Empty paragraph after table for spacing
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(6)


def format_table_header(row, col_widths=None):
    """Styles a table header row."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    for idx, cell in enumerate(row.cells):
        set_cell_background(cell, HEX_NAVY)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        if col_widths and idx < len(col_widths):
            cell.width = Inches(col_widths[idx])
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(8.5)
                r.font.bold = True
                r.font.color.rgb = WHITE


def format_table_row(row, is_even=False, col_widths=None):
    """Styles a table data row."""
    fill = HEX_LIGHT_BG if is_even else "FFFFFF"
    for idx, cell in enumerate(row.cells):
        set_cell_background(cell, fill)
        set_cell_margins(cell, top=80, bottom=80, left=140, right=140)
        if col_widths and idx < len(col_widths):
            cell.width = Inches(col_widths[idx])
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(8.5)
                r.font.color.rgb = CHARCOAL


def apply_table_borders(table):
    """Applies subtle border styling to table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{HEX_BORDER}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{HEX_BORDER}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def build_docx_from_markdown():
    if not MD_PATH.exists():
        raise FileNotFoundError(f"Markdown file not found: {MD_PATH}")

    with open(MD_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = Document()

    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)
        section.different_first_page_header_footer = True
        
        # Header / Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("A.R.G.U.S. — Milestones 7 & 8 Development Record")
        hrun.font.name = "Arial"
        hrun.font.size = Pt(8)
        hrun.font.color.rgb = MUTED
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("A.R.G.U.S. Academic PBL Prototype • Odd Semester 2026–27")
        frun.font.name = "Arial"
        frun.font.size = Pt(8)
        frun.font.color.rgb = MUTED

    # Cover Header Banner
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(12)
    title_p.paragraph_format.space_after = Pt(2)
    r_title = title_p.add_run("A.R.G.U.S. — Development Documentation")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(22)
    r_title.font.bold = True
    r_title.font.color.rgb = NAVY

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(8)
    r_sub = sub_p.add_run("Milestones 7 & 8: Security, Application/OOP & IoT Integration")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(14)
    r_sub.font.bold = True
    r_sub.font.color.rgb = BLUE

    tag_p = doc.add_paragraph()
    tag_p.paragraph_format.space_before = Pt(0)
    tag_p.paragraph_format.space_after = Pt(14)
    r_tag = tag_p.add_run("Technical Development Record — Current Development Session\n")
    r_tag.font.name = "Arial"
    r_tag.font.size = Pt(10.5)
    r_tag.font.italic = True
    r_tag.font.color.rgb = MUTED

    meta_runs = [
        ("Academic Year: ", True), ("2026–27 (Odd Semester)  |  ", False),
        ("Programme / Class: ", True), ("B.Tech AIML – C\n", False),
        ("Project: ", True), ("A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)\n", False),
        ("Mentor / Guide: ", True), ("Prof. Sunil Kale  |  ", False),
        ("Team: ", True), ("Savar Shetty, Pranav Pawar, Siddhesh Gire, Devraj Misal, Atharva Morbale", False),
    ]
    for text, bold in meta_runs:
        r = tag_p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(9)
        r.font.bold = bold
        r.font.color.rgb = CHARCOAL

    # Horizontal divider rule
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(14)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="{HEX_NAVY}"/></w:pBdr>')
    p_div._p.get_or_add_pPr().append(pBdr)

    # State machine for parsing markdown lines
    in_code = False
    code_lang = ""
    code_buffer = []

    in_table = False
    table_rows = []

    in_callout = False
    callout_text = []
    callout_title = "CRITICAL NOTICE"

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\r\n")

        # Code block handling
        if line.startswith("```"):
            if in_code:
                # End of code block
                in_code = False
                code_text = "\n".join(code_buffer)
                
                # Render code box
                tbl = doc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = False
                cell = tbl.cell(0, 0)
                cell.width = Inches(6.5)
                set_cell_background(cell, HEX_CODE_BG)
                set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                apply_table_borders(tbl)
                
                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                crun = cp.add_run(code_text)
                crun.font.name = "Consolas"
                crun.font.size = Pt(8)
                crun.font.color.rgb = CODE_COLOR

                p_sp = doc.add_paragraph()
                p_sp.paragraph_format.space_before = Pt(0)
                p_sp.paragraph_format.space_after = Pt(4)
                
                code_buffer = []
                i += 1
                continue
            else:
                in_code = True
                code_lang = line[3:].strip()
                code_buffer = []
                i += 1
                continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        # Callout handling (> [!NOTE], > [!IMPORTANT], > [!WARNING])
        if line.startswith("> [!"):
            m = re.match(r"> \[!(NOTE|IMPORTANT|WARNING|CAUTION|TIP)\]", line)
            callout_title = m.group(1) if m else "NOTICE"
            in_callout = True
            callout_text = []
            i += 1
            continue

        if in_callout:
            if line.startswith(">"):
                callout_text.append(line.lstrip("> ").strip())
                i += 1
                continue
            else:
                in_callout = False
                add_callout(doc, " ".join(callout_text), title=callout_title)
                callout_text = []
                # Fall through to process current line

        # Table handling
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            # Check if separator row (| :--- | :--- |)
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        elif in_table:
            # End of table
            in_table = False
            if table_rows:
                num_cols = max(len(r) for r in table_rows)
                tbl = doc.add_table(rows=len(table_rows), cols=num_cols)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = False
                apply_table_borders(tbl)

                # Estimate column widths
                total_width = 6.5
                col_w = total_width / num_cols
                col_widths = [col_w] * num_cols

                for r_idx, r_data in enumerate(table_rows):
                    row = tbl.rows[r_idx]
                    is_header = (r_idx == 0)
                    for c_idx in range(num_cols):
                        val = r_data[c_idx] if c_idx < len(r_data) else ""
                        cell = row.cells[c_idx]
                        cell.text = val
                    if is_header:
                        format_table_header(row, col_widths)
                    else:
                        format_table_row(row, is_even=(r_idx % 2 == 0), col_widths=col_widths)

                p_sp = doc.add_paragraph()
                p_sp.paragraph_format.space_before = Pt(0)
                p_sp.paragraph_format.space_after = Pt(6)
            table_rows = []
            # Fall through to process current line

        # Blank lines
        if not line.strip():
            i += 1
            continue

        # Skip main markdown title if already rendered in cover
        if line.startswith("# A.R.G.U.S.") or line.startswith("## Milestones 7 & 8") or line.startswith("### Technical Development"):
            i += 1
            continue

        # Headings
        if line.startswith("## "):
            h_text = line[3:].strip()
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(14)
            hp.paragraph_format.space_after = Pt(4)
            hp.paragraph_format.keep_with_next = True
            hrun = hp.add_run(h_text)
            hrun.font.name = "Arial"
            hrun.font.size = Pt(13)
            hrun.font.bold = True
            hrun.font.color.rgb = NAVY
            i += 1
            continue

        if line.startswith("### "):
            h_text = line[4:].strip()
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(10)
            hp.paragraph_format.space_after = Pt(3)
            hp.paragraph_format.keep_with_next = True
            hrun = hp.add_run(h_text)
            hrun.font.name = "Arial"
            hrun.font.size = Pt(11)
            hrun.font.bold = True
            hrun.font.color.rgb = BLUE
            i += 1
            continue

        if line.startswith("#### "):
            h_text = line[5:].strip()
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(8)
            hp.paragraph_format.space_after = Pt(2)
            hp.paragraph_format.keep_with_next = True
            hrun = hp.add_run(h_text)
            hrun.font.name = "Arial"
            hrun.font.size = Pt(9.5)
            hrun.font.bold = True
            hrun.font.color.rgb = TEAL
            i += 1
            continue

        # Bullet lists
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            bp = doc.add_paragraph(style="List Bullet")
            bp.paragraph_format.space_before = Pt(0)
            bp.paragraph_format.space_after = Pt(2)
            # Parse bold markdown (**text**)
            parts = re.split(r"(\*\*.*?\*\*)", bullet_text)
            for pt in parts:
                if pt.startswith("**") and pt.endswith("**"):
                    r = bp.add_run(pt[2:-2])
                    r.font.name = "Arial"
                    r.font.size = Pt(9)
                    r.font.bold = True
                    r.font.color.rgb = CHARCOAL
                else:
                    r = bp.add_run(pt)
                    r.font.name = "Arial"
                    r.font.size = Pt(9)
                    r.font.color.rgb = CHARCOAL
            i += 1
            continue

        # Numbered lists (1. , 2. )
        m_num = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m_num:
            num = m_num.group(1)
            num_text = m_num.group(2)
            np = doc.add_paragraph(style="List Number")
            np.paragraph_format.space_before = Pt(0)
            np.paragraph_format.space_after = Pt(2)
            parts = re.split(r"(\*\*.*?\*\*)", num_text)
            for pt in parts:
                if pt.startswith("**") and pt.endswith("**"):
                    r = np.add_run(pt[2:-2])
                    r.font.name = "Arial"
                    r.font.size = Pt(9)
                    r.font.bold = True
                    r.font.color.rgb = CHARCOAL
                else:
                    r = np.add_run(pt)
                    r.font.name = "Arial"
                    r.font.size = Pt(9)
                    r.font.color.rgb = CHARCOAL
            i += 1
            continue

        # Regular Body Paragraphs
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        parts = re.split(r"(\*\*.*?\*\*|\`.*?\`|\*.*?\*)", line)
        for pt in parts:
            if pt.startswith("**") and pt.endswith("**"):
                r = p.add_run(pt[2:-2])
                r.font.name = "Arial"
                r.font.size = Pt(9)
                r.font.bold = True
                r.font.color.rgb = CHARCOAL
            elif pt.startswith("`") and pt.endswith("`"):
                r = p.add_run(pt[1:-1])
                r.font.name = "Consolas"
                r.font.size = Pt(8.5)
                r.font.color.rgb = CODE_COLOR
            elif pt.startswith("*") and pt.endswith("*") and not pt.startswith("**"):
                r = p.add_run(pt[1:-1])
                r.font.name = "Arial"
                r.font.size = Pt(9)
                r.font.italic = True
                r.font.color.rgb = CHARCOAL
            else:
                r = p.add_run(pt)
                r.font.name = "Arial"
                r.font.size = Pt(9)
                r.font.color.rgb = CHARCOAL

        i += 1

    # Flush any remaining table or callout
    if in_callout and callout_text:
        add_callout(doc, " ".join(callout_text), title=callout_title)

    # Save document
    doc.save(DOCX_PATH)
    print(f"[+] Successfully generated Microsoft Word document at: {DOCX_PATH}")
    file_size_kb = DOCX_PATH.stat().st_size / 1024
    print(f"[+] File Size: {file_size_kb:.2f} KB")


if __name__ == "__main__":
    build_docx_from_markdown()
