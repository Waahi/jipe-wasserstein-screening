# -*- coding: utf-8 -*-
"""Editable PPTX twin of Fig 1 (five-gate protocol phase map).

Mirrors the matplotlib layout in fig1_five_gate_protocol.py one-for-one, using native
PowerPoint shapes so the user can hand-tweak wording, spacing and colours and have the
change flow back into the paper. Icons are placeholders that name the vector in the PDF,
since the icons are the one part that is easier to keep in the vector file.

Geometry mapping: figure data units (183 x 114) -> slide inches, y flipped.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- palette mirrored from the figure ----
VERM = RGBColor(0xC9, 0x6F, 0x8A); GREEN = RGBColor(0x00, 0x9E, 0x73)   # accent kept in step with the figure
BLUE = RGBColor(0x00, 0x72, 0xB2)
INK = RGBColor(0x22, 0x22, 0x22); DGRY = RGBColor(0x33, 0x33, 0x33)
MGRY = RGBColor(0x66, 0x66, 0x66); LGRY = RGBColor(0xCC, 0xCC, 0xCC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PANF = RGBColor(0xF2, 0xF4, 0xF7); FILL = RGBColor(0xE2, 0xE7, 0xEC)
PASSF = RGBColor(0xE8, 0xF4, 0xEF); FAILF = RGBColor(0xF9, 0xEE, 0xF1)
NAF = RGBColor(0xED, 0xEF, 0xF2)
ICONF = RGBColor(0xE9, 0xEC, 0xF0)
CORE_ICONF = RGBColor(0xF3, 0xE1, 0xE6)

# ---- canvas / mapping (identical numbers to the matplotlib script) ----
W, H = 183.0, 114.0
SW_IN, SH_IN = 13.333, 13.333 * H / W
prs = Presentation()
prs.slide_width = Inches(SW_IN); prs.slide_height = Inches(SH_IN)
slide = prs.slides.add_slide(prs.slide_layouts[6])


def X(x): return Inches(x / W * SW_IN)
def Y(y): return Inches((H - y) / H * SH_IN)          # flip
def DX(w): return Inches(w / W * SW_IN)
def DY(h): return Inches(h / H * SH_IN)


def box(x, y, w, h, fc, ec, lw=0.75, r=True, z=None):
    """x,y = lower-left in data coords (matplotlib convention)."""
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if r else MSO_SHAPE.RECTANGLE,
        X(x), Y(y + h), DX(w), DY(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = fc
    if ec is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = ec; shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    try:
        shp.adjustments[0] = 0.10
    except Exception:
        pass
    shp.text_frame.text = ""
    return shp


def dot(cx, cy, d, fc, ec, lw=1.0):
    """Small filled or hollow circle marking whether a gate issued a verdict.

    Follows the same lower-left data convention as box(), so cx, cy is the centre.
    """
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                X(cx - d / 2), Y(cy + d / 2), DX(d), DY(d))
    sh.fill.solid(); sh.fill.fore_color.rgb = fc
    sh.line.color.rgb = ec; sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    return sh


def txt(x, y, w, h, s, size=8, col=INK, bold=False, align=PP_ALIGN.CENTER):
    """x,y = lower-left of the text box in data coords."""
    tb = slide.shapes.add_textbox(X(x), Y(y + h), DX(w), DY(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = line
        r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = col
        r.font.name = "Helvetica"
    return tb


def conn(x1, y1, x2, y2, col, lw=1.0, arrow=True, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, X(x1), Y(y1), X(x2), Y(y2))
    c.line.color.rgb = col; c.line.width = Pt(lw)
    if dash:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    if arrow:   # arrowhead via XML (python-pptx has no high-level API for it)
        ln = c.line._get_or_add_ln()
        from pptx.oxml.ns import qn
        from lxml import etree
        tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type", "triangle")
        tail.set("w", "med"); tail.set("len", "med")
    return c


# ---- geometry (mirrors the matplotlib script) ----
LABW = 19.0
MG_L, MG_R, GAP, NG = 21.5, 180.0, 2.6, 5
PW = (MG_R - MG_L - (NG - 1) * GAP) / NG
XS = [MG_L + i * (PW + GAP) for i in range(NG)]
STRIP_Y = 108.5
G_TOP, G_BOT = 101.5, 65.0
RAIL_TOP, RAIL_BOT = 61.8, 53.6
S1_TOP, S1_BOT = 50.0, 35.0
S2_TOP, S2_BOT = 30.2, 15.2
RIB_Y = 2.6
CORE = 1

P = dict(margin="0.005", pth_lo="0.0003", pth_hi="0.0012", n_cells="9", pooled_dr="+0.042",
         eps_zero_share="86.3", moot_share="54.6", saa_ceil="54.8", w1_ceil="58.8",
         maint_routine="99.8", build_unsup="63.9", wilks_conf="91.5", wilks_n="48",
         origins="35")

GATES = [
    ("G1", "Structural\nsensitivity", "Can robustness change\nthe decision at all?",
     "degenerate if the radius\nterm is decision-free", "icon: decision fork"),
    ("G2", "Targetability\n(PTH screen)", "Is tail risk predictably\npersistent across units?",
     "advisory here:\nreport, do not stop", "icon: rank persistence"),
    ("G3", "Budget\ntightness", "Is a uniform cushion\nalready service sufficient?",
     "nothing to reallocate\nif the excess is zero", "icon: headroom gauge"),
    ("G4", "Fair-frontier\ncomparison", "Does it beat the uniform-\ncushion frontier?",
     "equivalent if the band\nstays within the margin", "icon: matched frontiers"),
    ("G5", "Implementability", "Is the prescription\nhistorically deliverable?",
     "routine only within the\nunit's own history", "icon: pile and own history"),
]

# ---- top strip ----
# Kept in sync with fig1_five_gate_protocol.py; see the phase-label note there.
for (i0, i1, s) in [(0, 2, "Early screening   (before any outcome comparison)"),
                    (3, 4, "Pre-deployment   (outcomes, then deliverability)")]:
    bx = XS[i0]; bw = XS[i1] + PW - XS[i0]
    box(bx, STRIP_Y - 3.5, bw, 7.0, WHITE, DGRY, 1.0)
    txt(bx, STRIP_Y - 3.0, bw, 6.0, s, 10.5, INK, True)
conn(XS[2] + PW + 0.4, STRIP_Y, XS[3] - 0.4, STRIP_Y, DGRY, 1.4)

# ---- gate panels ----
for i, (tag, name, q, rule, iconlab) in enumerate(GATES):
    core = (i == CORE)
    ec = VERM if core else LGRY
    box(XS[i], G_BOT, PW, G_TOP - G_BOT, WHITE if core else PANF, ec, 1.6 if core else 0.8)
    box(XS[i] + 1.4, G_TOP - 4.4, 7.0, 3.8, WHITE, VERM if core else MGRY, 0.7)
    txt(XS[i] + 1.4, G_TOP - 4.4, 7.0, 3.8, tag, 8, VERM if core else MGRY, True)
    txt(XS[i] + 8.8, G_TOP - 5.6, PW - 10.0, 5.4, name, 9.5, VERM if core else DGRY, True)
    box(XS[i] + 2.4, G_TOP - 22.4, PW - 4.8, 13.6, CORE_ICONF if core else ICONF, None)
    txt(XS[i] + 2.4, G_TOP - 20.0, PW - 4.8, 6.0, iconlab, 7.5, MGRY)
    txt(XS[i] + 1.6, G_TOP - 29.0, PW - 3.2, 6.0, q, 8.2, DGRY)
    box(XS[i] + 2.4, G_BOT + 1.5, PW - 4.8, 7.4, FAILF if core else WHITE,
        ec if core else LGRY, 0.7)
    txt(XS[i] + 2.4, G_BOT + 1.8, PW - 4.8, 6.8, rule, 7.4, VERM if core else MGRY)
    if i < NG - 1:
        ymid = (G_TOP + G_BOT) / 2
        conn(XS[i] + PW + 0.4, ymid, XS[i + 1] - 0.4, ymid, DGRY, 1.2)
        txt(XS[i] + PW, ymid + 1.2, GAP + 0.8, 3.0, "continue", 7.0, DGRY, True)
    ex_pass = (i == NG - 1)
    conn(XS[i] + PW / 2, G_BOT - 0.3, XS[i] + PW / 2, RAIL_TOP + 0.3,
         GREEN if ex_pass else VERM, 1.0)
    txt(XS[i] + PW / 2 + 1.2, (G_BOT + RAIL_TOP) / 2 - 1.5, 9.0, 3.0,
        "pass" if ex_pass else "fail", 6.8, GREEN if ex_pass else VERM, True, PP_ALIGN.LEFT)

txt(0.5, G_TOP + 0.8, 6.0, 5.0, "a", 14, INK, True)
txt(0.5, (G_TOP + G_BOT) / 2 + 0.6, LABW, 6.0, "Five-gate\nprotocol", 10.5, INK, True)
txt(0.5, (G_TOP + G_BOT) / 2 - 8.4, LABW, 7.0, "fixed order;\ngates 1, 3, 4, 5\nstop, gate 2 is\nadvisory here",
    7.4, MGRY)

# ---- worked paths, shape only ----
# No verdict word and no reported value here either. Filled marker: the gate issued a verdict for
# that study. Hollow: it did not. The verdicts are in the cross-study table.
PATHS = [
    ("b", "Study I\ncontrolled", 57.0, [True, False, True, True, False],
     "conclusion reached at gate 4; gate 5 not identifiable here"),
    ("c", "Study II\nEIA-923 coal", 45.0, [True, False, True, True, True],
     "conclusion reached at gates 4 and 5"),
]
for (lab, name, y, issued, end) in PATHS:
    txt(0.5, y + 3.0, 6.0, 5.0, lab, 14, INK, True)
    txt(0.5, y - 3.0, LABW, 6.0, name, 10.5, INK, True)
    conn(XS[0] + 1.0, y, XS[NG - 1] + PW - 1.0, y, VERM, 1.6, arrow=False)
    for i, hit in enumerate(issued):
        dot(XS[i] + PW / 2, y, 2.5, VERM if hit else WHITE, VERM, 1.1)
    txt(XS[0] + 1.0, y - 6.2, 90.0, 3.2, end, 7.0, MGRY, False, PP_ALIGN.LEFT)
txt(0.5, 37.0, LABW + 14.0, 6.0,
    "filled: the gate issued a verdict\nhollow: no verdict issued", 7.0, MGRY)

path = os.path.join(OUT, "fig1_five_gate_protocol.pptx")
prs.save(path)
print("wrote", os.path.basename(path))
