# -*- coding: utf-8 -*-
"""Graphical abstract in the layout of recently published JIPE graphical abstracts.

Redesigned 2026-07-30 against two published JIPE examples the co-authors supplied. Both share one
skeleton, and this file follows it: a full-width title banner, a left-to-right story strip of small
icons joined by ">>" marks, and three labelled columns (Background / Method / Findings) whose headers
sit in pills over content boxes. The earlier minimal design, one screen with three parallel
disposition arrows, is superseded by this venue-styled overview.

What survives from the earlier design because it was load-bearing rather than stylistic:

- **No hit rate is implied anywhere.** The paper states it has not measured how often a robust layer
  is added unnecessarily, so no element here sizes, colors, or orders outcomes by likelihood.
- **The honesty line rides along**: specificity demonstrated, sensitivity not established, printed on
  the canvas rather than left to a caption the abstract travels without.
- The palette is the paper's own (teal / navy / light gray, accent #C96F8A), not the example papers'
  greens, so the abstract reads as part of this figure set.

The journal caps width at 525 pixels, so the canvas is exactly 525 px wide and every label is placed
by hand. The numeric self-check from the previous design is kept: every text must sit inside the
canvas and no two texts may overlap, so a label pushed off the edge or onto a neighbour fails the
build rather than shipping.
"""
import os

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Polygon

OUT = os.path.dirname(os.path.abspath(__file__))

# The paper's palette, as used by Figures 2 to 4.
INK = "#222222"
MGRY = "#666666"
HAIR = "#D7DCE1"
LGRY = "#D3D5D4"
PANF = "#F4F6F8"
TEAL = "#93C8C0"
TEAL_INK = "#4A8F84"
MTEAL = "#4E9692"
NAVY = "#1C3C63"
ACC = "#C96F8A"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "axes.unicode_minus": False,
})

W, H = 525.0, 315.0                      # pixels at the 100 dpi used below
fig = plt.figure(figsize=(W / 100.0, H / 100.0))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")
ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="none", zorder=0))

TEXTS = []   # every text is registered so the self-check can find it


def T(x, y, s, fs, col=INK, w="normal", ha="center", va="center", style="normal", z=6, lsp=1.25):
    t = ax.text(x, y, s, fontsize=fs, color=col, fontweight=w, ha=ha, va=va,
                fontstyle=style, zorder=z, linespacing=lsp)
    TEXTS.append((s.replace("\n", " / ")[:40], t))
    return t


def box(x, y, w, h, fc="white", ec=HAIR, lw=0.8, r=3.0, z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, zorder=z)
    ax.add_patch(p)
    return p


# ---------------------------------------------------------------- title banner
box(6, H - 34, W - 12, 28, fc=NAVY, ec="none", r=4.0)
T(W / 2, H - 20, "Evaluating Wasserstein-robust inventory decisions before adoption",
  8.6, "white", "bold")

# ---------------------------------------------------------------- story strip
# Four nodes joined by ">>", as in both published examples: data, design, candidate, protocol.
NODE_X = [72, 199, 326, 453]
ICON_Y = H - 56
STRIP_LABELS = [
    "EIA-923 plant-level\ncoal stocks 2018–2024",
    "6,606 plant-origins\n35 rolling origins",
    "Wasserstein service\npolicy, radius ε",
    "five ordered gates,\nverdicts with license",
]


def ic_pile(cx, cy):
    ax.add_patch(Polygon([(cx - 11, cy - 6), (cx - 3, cy + 5), (cx + 2, cy - 0.5),
                          (cx + 6, cy + 3), (cx + 11, cy - 6)],
                         closed=True, fc=NAVY, ec="none", zorder=6))


def ic_roll(cx, cy):
    ax.add_patch(FancyArrowPatch((cx - 7, cy - 4), (cx + 7, cy - 4),
                                 connectionstyle="arc3,rad=-0.9", arrowstyle="-|>",
                                 mutation_scale=6, color=TEAL_INK, lw=1.2, zorder=6))
    ax.add_patch(Circle((cx, cy - 2.5), 1.4, fc=TEAL_INK, ec="none", zorder=6))


def ic_ball(cx, cy):
    ax.add_patch(Circle((cx, cy - 1), 7.5, fc=TEAL, ec=TEAL_INK, lw=1.0, zorder=6))
    ax.add_patch(Circle((cx, cy - 1), 1.2, fc=NAVY, ec="none", zorder=7))
    ax.plot([cx, cx + 6.6], [cy - 1, cy + 2.2], color=NAVY, lw=0.9, zorder=7)


def ic_gates(cx, cy):
    for k in range(5):
        x = cx - 10 + k * 5
        ax.add_patch(Rectangle((x, cy - 6), 3.2, 11, fc=(LGRY if k == 1 else NAVY),
                               ec="none", zorder=6))


for f, cx in zip([ic_pile, ic_roll, ic_ball, ic_gates], NODE_X):
    f(cx, ICON_Y)
for cx, lab in zip(NODE_X, STRIP_LABELS):
    T(cx, ICON_Y - 17, lab, 5.0, INK)
for a, b in zip(NODE_X[:-1], NODE_X[1:]):
    T((a + b) / 2, ICON_Y - 4, ">>", 8.0, ACC, "bold")

# ---------------------------------------------------------------- three columns
COL_Y0, COL_Y1 = 16, H - 96              # content boxes span this band
CW = 163.0
COL_X = [7.0, 181.0, 355.0]
HEADS = ["Background", "Method", "Findings"]

for x0, head in zip(COL_X, HEADS):
    box(x0, COL_Y0, CW, COL_Y1 - COL_Y0, fc=PANF, ec=HAIR, lw=0.8)
    box(x0 + CW / 2 - 46, COL_Y1 - 9, 92, 17, fc=MTEAL, ec="none", r=6.0, z=5)
    T(x0 + CW / 2, COL_Y1 - 0.5, head, 6.8, "white", "bold", z=7)

# Background column ------------------------------------------------------------
bx = COL_X[0] + 9
BULLETS = [
    "• A robust layer costs: build,\n   calibrate, explain",
    "• Q1  Can it change the\n   decision at all?",
    "• Q2  Do the data support\n   differentiated protection?",
    "• Benchmark: uniform cushion\n   at matched inventory",
]
by = COL_Y1 - 26
for s in BULLETS:
    T(bx, by, s, 5.1, INK, ha="left", va="top")
    by -= 47

# Method column ----------------------------------------------------------------
mx = COL_X[1] + 8
GATES = [
    ("G1", "structural sensitivity", 20),
    ("G2", "targetability (advisory)", 20),
    ("G3", "budget tightness", 20),
    ("G4", "fair frontier,\nmatched inventory", 28),
    ("G5", "implementability", 20),
]
gy = COL_Y1 - 14
for g, lab, gh in GATES:
    box(mx, gy - gh, CW - 16, gh, fc="white", ec=(ACC if g == "G2" else NAVY), lw=0.9, r=2.5, z=4)
    T(mx + 10, gy - gh / 2, g, 5.3, (ACC if g == "G2" else NAVY), "bold", z=7)
    T(mx + 21, gy - gh / 2, lab, 5.0, INK, ha="left", z=7, lsp=1.1)
    gy -= gh
    if g != "G5":
        ax.add_patch(Polygon([(mx + (CW - 16) / 2 - 3, gy - 1.8),
                              (mx + (CW - 16) / 2 + 3, gy - 1.8),
                              (mx + (CW - 16) / 2, gy - 6.2)],
                             closed=True, fc=MGRY, ec="none", zorder=7))
        gy -= 10
T(COL_X[1] + CW / 2, COL_Y0 + 12, "stopping rules at G1, G3, G4, G5;\nG2 is reported, not a stop",
  4.5, MGRY, style="italic")

# Findings column --------------------------------------------------------------
fx = COL_X[2] + 9
# Both headline verdicts appear, controlled and field. Showing only the field results would be a
# selective display of the two studies the paper reports with equal weight.
FIND = [
    ("Cost form: certified redundant", "robust = empirical prescription\nat every radius"),
    ("Controlled study: materially worse", "on the reliability criterion\nin all nine cells"),
    ("Field study: equivalent", "matches quantile-plus-cushion at\nmatched inventory, 52–58 days"),
    ("Pile-build rarely supported", "63.9% of pile-build targets\nexceed the plant's own precedent"),
]
fy = COL_Y1 - 20
for head, bod in FIND:
    T(fx, fy, head, 5.4, NAVY, "bold", ha="left", va="top")
    T(fx, fy - 10, bod, 5.0, INK, ha="left", va="top")
    fy -= 45

# ---------------------------------------------------------------- honesty line
T(W / 2, 8, "stopping specificity demonstrated in the cases studied; sensitivity not established",
  4.5, MGRY, style="italic")

# ---------------------------------------------------------------- self-check
fig.canvas.draw()
inv = ax.transData.inverted()
BOXES = []
for label, artist in TEXTS:
    bb = artist.get_window_extent(fig.canvas.get_renderer())
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    BOXES.append((label, x0, y0, x1, y1))

clipped = [b[0] for b in BOXES if b[1] < 1 or b[3] > W - 1 or b[2] < 1 or b[4] > H - 1]
if clipped:
    raise SystemExit(f"label runs off the canvas: {clipped}")

overlaps = []
for i in range(len(BOXES)):
    for j in range(i + 1, len(BOXES)):
        a, b = BOXES[i], BOXES[j]
        if min(a[3], b[3]) - max(a[1], b[1]) > 1 and min(a[4], b[4]) - max(a[2], b[2]) > 1:
            overlaps.append((a[0], b[0]))
if overlaps:
    raise SystemExit(f"labels overlap: {overlaps}")
print(f"layout check: {len(BOXES)} labels, none clipped, none overlapping")

base = os.path.join(OUT, "GraphicalAbstract1")
fig.savefig(base + ".png", dpi=100, facecolor="white")
fig.savefig(base + ".tiff", dpi=100, facecolor="white")
plt.close(fig)

from PIL import Image
for ext in (".png", ".tiff"):
    with Image.open(base + ext) as im:
        print(f"wrote GraphicalAbstract1{ext}  {im.size[0]} x {im.size[1]} px")
        if im.size[0] != 525:
            raise SystemExit(f"width is {im.size[0]} px, the journal caps it at 525")
