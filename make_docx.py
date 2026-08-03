# -*- coding: utf-8 -*-
"""Convert the built markdown into the Word files the journal actually accepts.

The journal takes "any standard format, including Word and LaTeX". Markdown is neither, so the
package cannot be submitted as it stands. There is no pandoc on this machine, so this is a narrow
converter for the markdown this project generates rather than a general one, and it is deliberately
strict: anything it does not recognise raises instead of being dropped, because a converter that
silently discards a paragraph produces a plausible-looking file that is missing part of the paper.

Markdown tables become real Word tables. The checklist asks for editable table files, and a table
flattened into text is not editable.

Superscript affiliation markers, bold, italic and inline code are carried through as runs so the
title page and the frozen vocabulary survive the conversion.
"""
import io
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

D = os.path.dirname(os.path.abspath(__file__))

# ``**bold**``, ``*italic*``, ``` `code` ``` and ``^sup^``, in one pass so nesting cannot reorder them
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\^[^^\s]+\^)")


def add_runs(par, text):
    for chunk in INLINE.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**"):
            par.add_run(chunk[2:-2]).bold = True
        elif chunk.startswith("`") and chunk.endswith("`"):
            # Inline mathematics. Goto's comment (i): the running-text symbols and the displayed
            # equations rendered in different fonts, because inline code went to Consolas while
            # display blocks went to Cambria Math. One face for both, and make_submission asserts
            # no Consolas run survives in any shipped DOCX.
            r = par.add_run(chunk[1:-1])
            r.font.name = "Cambria Math"
            r.font.size = Pt(10.5)
        elif chunk.startswith("^") and chunk.endswith("^"):
            r = par.add_run(chunk[1:-1])
            r.font.superscript = True
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            par.add_run(chunk[1:-1]).italic = True
        else:
            par.add_run(chunk)


def is_table_row(line):
    return line.strip().startswith("|")


def is_rule_row(line):
    return bool(re.fullmatch(r"\s*\|[\s:|-]+\|\s*", line))


def convert(md_path, docx_path, title=None):
    lines = io.open(md_path, encoding="utf-8").read().split("\n")
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    i, n_par, n_tab = 0, 0, 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        if not line.strip():
            i += 1
            continue

        # horizontal rules separate the assembled blocks and carry no content
        if re.fullmatch(r"\s*-{3,}\s*", line):
            i += 1
            continue

        # tables
        if is_table_row(line):
            block = []
            while i < len(lines) and is_table_row(lines[i]):
                block.append(lines[i])
                i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")]
                    for r in block if not is_rule_row(r)]
            if not rows:
                continue
            width = max(len(r) for r in rows)
            tbl = doc.add_table(rows=0, cols=width)
            tbl.style = "Table Grid"
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            for k, row in enumerate(rows):
                cells = tbl.add_row().cells
                for c, val in enumerate(row):
                    cells[c].text = ""
                    p = cells[c].paragraphs[0]
                    add_runs(p, val)
                    for r in p.runs:
                        r.font.size = Pt(9)
                        if k == 0:
                            r.bold = True
            n_tab += 1
            continue

        # images, written as ![](path). Used by the reading copy, which places each figure inline;
        # the submission files never contain one, because that package uploads figures separately.
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", line.strip())
        if m:
            path = m.group(1)
            if not os.path.isabs(path):
                path = os.path.join(D, path)
            if not os.path.exists(path):
                raise SystemExit(f"figure file missing, refusing to build a copy without it: {path}")
            # Fit inside the text block both ways. Sizing on width alone pushes a tall figure past
            # the bottom of the page, and Word then shrinks it silently at print time.
            from PIL import Image
            from docx.shared import Inches
            with Image.open(path) as im:
                w_px, h_px = im.size
                dpi = im.info.get("dpi", (96, 96))[0] or 96
            # Cap at the image's own dpi-implied natural size as well as the text block: the
            # 525 px graphical abstract must not be upscaled into blur just to fill the column.
            max_w, max_h = min(6.2, w_px / dpi), 7.8
            w_in = max_w
            if h_px / w_px * w_in > max_h:
                w_in = max_h * w_px / h_px
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(path, width=Inches(w_in))
            n_par += 1
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            doc.add_heading(re.sub(r"[*`]", "", m.group(2)), level=min(level, 3))
            i += 1
            continue

        # block quotes carry the formal statements
        if line.lstrip().startswith(">"):
            block = []
            while i < len(lines) and (lines[i].lstrip().startswith(">") or not lines[i].strip()):
                if not lines[i].strip():
                    if block and block[-1] == "":
                        break
                    block.append("")
                else:
                    block.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            for chunk in "\n".join(block).split("\n\n"):
                if not chunk.strip():
                    continue
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Pt(24)
                add_runs(p, " ".join(x.strip() for x in chunk.split("\n")))
                n_par += 1
            continue

        # indented display equations
        if raw.startswith("    ") and raw.strip():
            block = []
            while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
                if lines[i].strip():
                    block.append(lines[i].strip())
                elif block:
                    break
                i += 1
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run("\n".join(block))
            r.font.name = "Cambria Math"
            n_par += 1
            continue

        # ordinary paragraph: join its wrapped lines
        block = []
        while i < len(lines) and lines[i].strip() and not is_table_row(lines[i]) \
                and not lines[i].lstrip().startswith(">") and not lines[i].startswith("#") \
                and not lines[i].startswith("    ") \
                and not re.fullmatch(r"\s*-{3,}\s*", lines[i]):
            block.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        add_runs(p, " ".join(block))
        n_par += 1

    doc.save(docx_path)
    return n_par, n_tab


def main():
    jobs = [
        ("MANUSCRIPT_TITLE_PAGE.md", "Manuscript_with_author_details.docx"),
        ("MANUSCRIPT_ANON.md", "Manuscript_anonymous.docx"),
        ("SUPPLEMENT.md", "Supplementary_material.docx"),
    ]
    out = os.path.join(D, "submission")
    for src, dst in jobs:
        p = os.path.join(out, src)
        if not os.path.exists(p):
            sys.exit(f"missing built file: {src}; run make_submission.py first")
        n_par, n_tab = convert(p, os.path.join(out, dst))
        print(f"  {dst:<38} {n_par:>4} paragraphs, {n_tab} tables")


if __name__ == "__main__":
    main()
