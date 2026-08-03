# -*- coding: utf-8 -*-
"""Fig 1 for the JIPE paper "Evaluating Wasserstein-robust inventory decisions".

Five-gate pre-solve and pre-deployment protocol as a phase map, with both case studies
drawn as worked paths through the SAME gates (Codex Q8: the protocol, not either null
result, is the central reusable contribution).

House style follows this group's dense-grid figure convention (style reference only,
no data reused): Wong palette, rounded
FancyBboxPatch panels, FancyArrowPatch arrows, spine pills, top stage strip, bottom
keyword ribbon, icon-first minimal text, panel-filling layout, stars as polygons.

Core panel (vermilion, white fill against the tinted others) = Gate 2, the targetability
or PTH screen. All reported numbers are parameterised as named constants below.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Polygon, Wedge

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

# ---------------- palette / rc (house style) ----------------
BLUE = "#0072B2"; GREEN = "#009E73"
VERM = "#C96F8A"          # the accent, replacing the former vermilion; the only orange this figure drew
INK = "#222222"; DGRY = "#333333"; MGRY = "#666666"; LGRY = "#CCCCCC"
FILL = "#E2E7EC"; HAIR = "#D7DCE1"
PANF = "#F2F4F7"                                  # tinted gate panel (core stays white)
# The core gate's tinted rule box is the accent at about 12 per cent on white, so it follows the
# accent rather than staying a pale orange from the previous palette.
FAILF = "#F9EEF1"        # the accent at about 12 per cent on white, for the core gate's rule box
plt.rcParams.update({"font.family": "sans-serif",
                     "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
                     "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
                     "axes.unicode_minus": False})

# No reported quantity appears in this figure. It shows the protocol, not the results; the
# values and verdicts live in the cross-study table so that the two cannot drift apart.

# ---------------- canvas ----------------
# The gate coordinates are kept from the earlier design so the layout code did not have to move.
# Removing the verdict rail and the concept ribbon emptied the lower third, so the viewport now
# starts above it rather than at zero.
W, H = 183.0, 114.0
Y0 = 33.0
fig, AX = plt.subplots(figsize=(7.2, 7.2 * (H - Y0) / W))
AX.set_xlim(0, W); AX.set_ylim(Y0, H); AX.set_aspect("equal"); AX.axis("off")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

REG = []   # (id, artist, kind) for the bbox manifest and self-check


def T(x, y, s, fs=6, col=INK, w="normal", ha="center", va="center", z=8, id=None, lsp=1.32):
    t = AX.text(x, y, s, ha=ha, va=va, fontsize=fs, color=col, fontweight=w,
                zorder=z, linespacing=lsp)
    REG.append((id or ("t:" + s.replace("\n", " ")[:22]), t, "text")); return t


def panel(x, y, w, h, ec=LGRY, lw=0.7, fc="white", r=2.2, z=1, id=None, ls="-"):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.2,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
    AX.add_patch(p); REG.append((id or "panel", p, "panel")); return p


def arr(x1, y1, x2, y2, col=MGRY, lw=1.0, ms=9, z=4, ls="-"):
    AX.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms,
                                 color=col, lw=lw, ls=ls, shrinkA=0, shrinkB=0, zorder=z))


def Ln(x1, y1, x2, y2, z=5, **k):
    AX.plot([x1, x2], [y1, y2], zorder=z, **k)


def C(cx, cy, r, **k): AX.add_patch(Circle((cx, cy), r, **k))
def Rct(x, y, w, h, **k): AX.add_patch(Rectangle((x, y), w, h, **k))
def Pg(p, **k): AX.add_patch(Polygon(p, closed=True, **k))


def star(cx, cy, r, col, z=6):   # Arial lacks the star glyph, draw it as a polygon
    Pg([(cx + (r if k % 2 == 0 else r * 0.44) * np.cos(np.pi / 2 + k * np.pi / 5),
         cy + (r if k % 2 == 0 else r * 0.44) * np.sin(np.pi / 2 + k * np.pi / 5))
        for k in range(10)], fc=col, ec="none", zorder=z)


def pill(cx, cy, s, col, fs=4.4, wpx=5.0, hpx=3.0, z=8, id=None, fc="white"):
    p = FancyBboxPatch((cx - wpx / 2, cy - hpx / 2), wpx, hpx,
                       boxstyle="round,pad=0.05,rounding_size=0.8", fc=fc, ec=col,
                       lw=0.6, zorder=z)
    AX.add_patch(p); REG.append((id or ("pill:" + s), p, "panel"))
    T(cx, cy, s, fs, col, "bold", z=z + 1, id="pt:" + (id or s))


# ---------------- icons ----------------
def ic_fork(cx, cy, s=1.0):
    """Gate 1: one decision node, one live branch and one collapsed branch."""
    C(cx - 3.8 * s, cy, 1.1 * s, fc="white", ec=MGRY, lw=0.7, zorder=6)
    arr(cx - 2.6 * s, cy, cx + 2.9 * s, cy + 2.7 * s, col=VERM, lw=1.0, ms=6, z=6)
    arr(cx - 2.6 * s, cy, cx + 2.9 * s, cy - 2.7 * s, col=LGRY, lw=1.0, ms=6, z=6,
        ls=(0, (2.2, 1.5)))
    C(cx + 3.8 * s, cy + 3.0 * s, 0.95 * s, fc=VERM, ec="none", zorder=7)
    C(cx + 3.8 * s, cy - 3.0 * s, 0.95 * s, fc="white", ec=LGRY, lw=0.7, zorder=7)
    T(cx + 5.4 * s, cy + 3.0 * s, "moves", 3.6, VERM, "bold", ha="left", id="ic1a")
    T(cx + 5.4 * s, cy - 3.0 * s, "fixed", 3.6, MGRY, ha="left", id="ic1b")


def ic_rank(cx, cy, s=1.0):
    """Gate 2 (core): does the cross-unit risk ranking persist between blocks."""
    def blockpair(x0, col, cross, ys):
        for k in range(3):
            C(x0, cy + ys[k] * s, 0.68 * s, fc="white", ec=col, lw=0.75, zorder=6)
            C(x0 + 4.8 * s, cy + ys[k] * s, 0.68 * s, fc=col, ec="none", zorder=6)
        order = [2, 0, 1] if cross else [0, 1, 2]
        for k in range(3):
            Ln(x0 + 0.8 * s, cy + ys[k] * s, x0 + 4.0 * s, cy + ys[order[k]] * s,
               color=col, lw=0.8, alpha=0.95, z=5)
    ys = [2.9, 0.0, -2.9]
    blockpair(cx - 9.2 * s, GREEN, False, ys)
    blockpair(cx + 2.6 * s, MGRY, True, ys)
    T(cx - 6.8 * s, cy - 4.9 * s, "persistent", 3.7, GREEN, "bold", id="ic2a")
    T(cx + 5.0 * s, cy - 4.9 * s, "scrambled", 3.7, MGRY, id="ic2b")


def ic_gauge(cx, cy, s=1.0):
    """Gate 3: how much service headroom a uniform cushion already consumes."""
    AX.add_patch(Wedge((cx, cy - 1.2 * s), 3.4 * s, 0, 180, width=0.95 * s, fc=LGRY,
                       ec="none", zorder=5))
    AX.add_patch(Wedge((cx, cy - 1.2 * s), 3.4 * s, 118, 180, width=0.95 * s, fc=GREEN,
                       ec="none", zorder=6))
    a = np.radians(146)
    Ln(cx, cy - 1.2 * s, cx + 2.6 * s * np.cos(a), cy - 1.2 * s + 2.6 * s * np.sin(a),
       color=INK, lw=1.0, z=7)
    C(cx, cy - 1.2 * s, 0.45 * s, fc=INK, ec="none", zorder=7)
    T(cx, cy + 3.4 * s, "headroom", 3.7, MGRY, id="ic3a")


def ic_frontier(cx, cy, s=1.0):
    """Gate 4: two service-inventory frontiers compared at a matched resource level."""
    L, B = cx - 6.2 * s, cy - 3.9 * s
    Ln(L, B, L, B + 7.8 * s, color=MGRY, lw=0.6, z=5)
    Ln(L, B, L + 12.4 * s, B, color=MGRY, lw=0.6, z=5)
    xx = np.linspace(0.7, 11.8, 26)
    AX.plot(L + xx, B + (6.6 * np.exp(-0.28 * xx) + 0.6) * s, color=VERM, lw=1.1, zorder=6)
    AX.plot(L + xx, B + (6.6 * np.exp(-0.28 * (xx - 0.30)) + 0.45) * s, color=BLUE, lw=1.1,
            ls=(0, (2.6, 1.5)), zorder=6)
    Ln(L + 6.0 * s, B + 0.4 * s, L + 6.0 * s, B + 6.6 * s, color=MGRY, lw=0.5, z=5)
    T(L + 6.0 * s, B + 7.6 * s, "matched", 3.7, MGRY, id="ic4m")


def ic_pile(cx, cy, s=1.0):
    """Gate 5: can the target be reached from the unit's own delivery history."""
    Pg([(cx - 4.0 * s, cy - 3.0 * s), (cx + 4.0 * s, cy - 3.0 * s),
        (cx + 2.1 * s, cy + 0.9 * s), (cx - 2.1 * s, cy + 0.9 * s)],
       fc=FILL, ec=MGRY, lw=0.75, zorder=5)
    Ln(cx - 4.0 * s, cy + 3.1 * s, cx + 4.0 * s, cy + 3.1 * s, color=MGRY, lw=0.8, z=5)
    T(cx, cy + 4.4 * s, "own history", 3.7, MGRY, id="ic5cap")
    arr(cx - 6.2 * s, cy + 2.6 * s, cx - 1.1 * s, cy - 0.6 * s, col=BLUE, lw=1.0, ms=6, z=6)


# ---------------- layout geometry ----------------
LABW = 19.0
MG_L, MG_R, GAP, NG = 21.5, 180.0, 2.6, 5
PW = (MG_R - MG_L - (NG - 1) * GAP) / NG
XS = [MG_L + i * (PW + GAP) for i in range(NG)]
CXS = [x + PW / 2 for x in XS]

STRIP_Y = 108.5
G_TOP, G_BOT = 101.5, 65.0

CORE = 1                        # Gate 2, the targetability or PTH screen

GATES = [
    dict(tag="G1", name="Structural\nsensitivity",
         q="Can robustness change\nthe decision at all?",
         rule="degenerate if the radius\nterm is decision-free", icon=ic_fork),
    dict(tag="G2", name="Targetability\n(PTH screen)",
         q="Is tail risk predictably\npersistent across units?",
         rule="advisory here:\nreport, do not stop", icon=ic_rank),
    dict(tag="G3", name="Budget\ntightness",
         q="Is a uniform cushion\nalready service sufficient?",
         rule="nothing to reallocate\nif the excess is zero", icon=ic_gauge),
    dict(tag="G4", name="Fair-frontier\ncomparison",
         q="Does it beat the uniform-\ncushion frontier?",
         rule="equivalent if the band\nstays within the margin", icon=ic_frontier),
    dict(tag="G5", name="Implementability",
         q="Is the prescription\nhistorically deliverable?",
         rule="routine only within the\nunit's own history", icon=ic_pile),
]

# ---------------- top stage strip ----------------
# Phase labels, corrected 2026-07-30. The old pair claimed too much at both ends. "Pre-solve
# (training information only)" was wrong for gate 3, whose frequency-based form counts decision points
# where the candidate asks for more than the comparator and so needs the candidate solved, and that is
# the form both studies used. "matched-resource evaluation" was wrong for gate 5, which classifies
# prescriptions against own-history percentiles and does not itself match resources. The split that
# survives is whether an outcome comparison has happened yet.
for (i0, i1, txt) in [(0, 2, "Early screening   (before any outcome comparison)"),
                      (3, 4, "Pre-deployment   (outcomes, then deliverability)")]:
    bx = XS[i0]; bw = XS[i1] + PW - XS[i0]
    panel(bx, STRIP_Y - 3.5, bw, 7.0, ec=DGRY, lw=1.0, r=2.0, z=3, id=f"strip{i0}")
    T(bx + bw / 2, STRIP_Y, txt, 6.1, INK, "bold", id=f"stript{i0}")
arr(XS[2] + PW + 0.4, STRIP_Y, XS[3] - 0.4, STRIP_Y, col=DGRY, lw=1.3, ms=10)

# ---------------- gate panels ----------------
for i, g in enumerate(GATES):
    core = (i == CORE)
    ec = VERM if core else LGRY
    panel(XS[i], G_BOT, PW, G_TOP - G_BOT, ec=ec, lw=1.4 if core else 0.7,
          fc="white" if core else PANF, z=1, id=f"gate{i}")
    pill(XS[i] + 4.8, G_TOP - 2.6, g["tag"], VERM if core else MGRY, fs=4.7,
         wpx=6.8, hpx=3.6, id=f"gp{i}")
    T(CXS[i] + 2.8, G_TOP - 2.6, g["name"], 5.6, VERM if core else DGRY, "bold", id=f"gn{i}")
    Ln(XS[i] + 2.2, G_TOP - 7.2, XS[i] + PW - 2.2, G_TOP - 7.2, color=HAIR, lw=0.5, z=3)
    panel(XS[i] + 2.4, G_TOP - 22.4, PW - 4.8, 13.6, ec="none", lw=0.0,
          # the core gate's icon well is accent-tinted, matching its rule box
          fc=FILL if not core else "#F3E1E6", r=1.2, z=2, id=f"gib{i}")
    g["icon"](CXS[i], G_TOP - 15.4, 1.12)
    T(CXS[i], G_TOP - 26.0, g["q"], 4.8, DGRY, id=f"gq{i}")
    panel(XS[i] + 2.4, G_BOT + 1.5, PW - 4.8, 7.4, ec=ec if core else HAIR,
          lw=0.6, fc=FAILF if core else "white", r=1.3, z=2, id=f"gr{i}")
    T(CXS[i], G_BOT + 5.2, g["rule"], 4.3, VERM if core else MGRY, id=f"grt{i}")
    if i < NG - 1:
        ymid = (G_TOP + G_BOT) / 2
        arr(XS[i] + PW + 0.4, ymid, XS[i + 1] - 0.4, ymid, col=DGRY, lw=1.1, ms=9)
        T((XS[i] + PW + XS[i + 1]) / 2, ymid + 2.4, "continue", 4.0, DGRY, "bold", id=f"pass{i}")
    # stopping authority: gates 1, 3 and 4 can end the analysis, gate 5 ends it by carrying on,
    # and gate 2 has no exit at all in this paper. The arrows stop at a short stub rather than
    # running into a verdict row, because the verdicts belong to the cross-study table.
    STUB = G_BOT - 5.4
    exit_pass = (i == NG - 1)
    if i == CORE:
        T(CXS[i] + 1.6, (G_BOT + STUB) / 2, "no exit:\nadvisory", 3.8, MGRY, "bold",
          ha="left", id=f"exit{i}")
    else:
        arr(CXS[i], G_BOT - 0.3, CXS[i], STUB, col=GREEN if exit_pass else VERM,
            lw=0.9, ms=7, z=4)
        T(CXS[i] + 1.6, (G_BOT + STUB) / 2, "carry on" if exit_pass else "stop", 3.8,
          GREEN if exit_pass else VERM, "bold", ha="left", id=f"exit{i}")
T(XS[0] - 1.0, G_TOP + 3.2, "a", 8.5, INK, "bold", ha="right", id="lab_a")
T(LABW / 2 + 0.5, (G_TOP + G_BOT) / 2 + 3.4, "Five-gate\nprotocol", 6.4, INK, "bold", id="rl_a")
T(LABW / 2 + 0.5, (G_TOP + G_BOT) / 2 - 4.4, "fixed order;\ngates 1, 3, 4, 5\nstop, gate 2 is\nadvisory here",
  4.4, MGRY, id="rl_a2")
Ln(2.4, G_BOT + 2.0, 2.4, G_TOP - 2.0, color=VERM, lw=1.6, z=4)

# ---------------- worked paths, shape only ----------------
# Deliberately carries no verdict word and no reported value. A filled marker means the gate issued
# a verdict for that study, a hollow one means it did not: Gate 2 is advisory throughout, and Gate 5
# is not empirically identifiable in a simulation with no delivery history. The verdicts themselves,
# with their evidence and qualifiers, are in the cross-study table.
PATHS = [
    dict(lab="b", name="Study I\ncontrolled", y=57.0,
         issued=[True, False, True, True, False],
         end="conclusion reached at gate 4; gate 5 not identifiable here"),
    dict(lab="c", name="Study II\nEIA-923 coal", y=45.0,
         issued=[True, False, True, True, True],
         end="conclusion reached at gates 4 and 5"),
]
for s in PATHS:
    T(XS[0] - 1.0, s["y"] + 4.6, s["lab"], 8.5, INK, "bold", ha="right", id=f"lab_{s['lab']}")
    T(LABW / 2 + 0.5, s["y"], s["name"], 6.0, INK, "bold", id=f"rl_{s['lab']}")
    AX.plot([XS[0] + 1.0, XS[NG - 1] + PW - 1.0], [s["y"]] * 2, color=VERM, lw=1.4, zorder=5)
    for i, issued in enumerate(s["issued"]):
        C(CXS[i], s["y"], 1.25, fc=VERM if issued else "white", ec=VERM, lw=1.1, zorder=7)
    T(CXS[0], s["y"] - 4.4, s["end"], 4.4, MGRY, ha="left", id=f"{s['lab']}end")

T(LABW / 2 + 0.5, 37.0, "filled: the gate issued a verdict\nhollow: no verdict issued",
  4.4, MGRY, id="pathkey")

# ---------------- export and bbox manifest ----------------
fig.canvas.draw()
rend = fig.canvas.get_renderer()
inv = AX.transData.inverted()
boxes = []
for eid, art, kind in REG:
    try:
        bb = art.get_window_extent(renderer=rend)
    except Exception:
        continue
    (x0, y0) = inv.transform((bb.x0, bb.y0)); (x1, y1) = inv.transform((bb.x1, bb.y1))
    boxes.append(dict(id=eid, kind=kind, x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1)))
json.dump(dict(canvas=[W, H], boxes=boxes), open(os.path.join(OUT, "fig1_bbox.json"), "w"), indent=1)

base = os.path.join(OUT, "fig1_five_gate_protocol")
fig.savefig(base + ".png", dpi=600, bbox_inches="tight", pad_inches=0.03)
fig.savefig(base + ".pdf", bbox_inches="tight", pad_inches=0.03)
fig.savefig(base + ".svg", bbox_inches="tight", pad_inches=0.03)
plt.close(fig)
print("wrote fig1_five_gate_protocol .png/.pdf/.svg and fig1_bbox.json")
