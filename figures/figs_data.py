# -*- coding: utf-8 -*-
"""Data figures 2 to 4 for the six-section JIPE build.

Replaces figs2to5.py. The change is not cosmetic: under the 9,000-word structure the paper carries
four figures rather than five, and the two that reported Gate 4 of the field study are merged into a
single figure with two panels. They belonged together already, because panel (b) only means anything
once panel (a) has fixed which range both policies can actually reach.

  Figure 2  controlled study, Gate 4 simultaneous bands across the nine cells   (was Figure 2)
  Figure 3  field study Gate 4: (a) frontiers and ceilings, (b) matched-inventory
            paired differences by regime                                        (was Figures 3 and 4)
  Figure 4  field study Gate 5, historical support by regime                     (was Figure 5)

Palette, vocabulary and style rules are inherited unchanged from figs2to5.py so the paper still reads
as one system.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.gridspec import GridSpec

OUT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(OUT), "data")

# ---- approved data-figure palette --------------------------------------------------------------
# Fill colours. Two of them cannot carry a thin line: on white the teal measures 1.86:1 and the light
# gray 1.47:1, so anything narrow drawn in them disappears. Each therefore has a darker same-hue ink,
# and the rule is fills in the light colour, lines and marker edges in the ink.
NAVY = "#1C3C63"        # darkest, reserved for the series the reader should look at first
MTEAL = "#4E9692"       # only Figure 3 needs a fourth colour
TEAL = "#93C8C0"
LGREY = "#D3D5D4"
NAVY_INK = "#1C3C63"    # already dark enough to draw with
# The two teal-family series sit in the same overlapping cluster in Figure 3(a), so their line
# inks are pushed apart in lightness rather than left at neighbouring values: at greyscale 83
# against 127 they separate, where the first pairing differed by only 17 and read as one colour.
MTEAL_INK = "#22615C"
TEAL_INK = "#4A8F84"
LGREY_INK = "#7E827F"
EDGE = "#2E2E2E"        # crisp marker edge, so the pale fills stay defined

INK = "#222222"; MGRY = "#666666"; LGRY = "#CCCCCC"; HAIR = "#E3E7EB"
RELIABILITY_MARGIN_PP = 0.005   # probability points, worst-decile service excess
SHORTFALL_MARGIN_MDU = 0.005    # mean-demand units, expected shortfall
MARGIN = SHORTFALL_MARGIN_MDU
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.unicode_minus": False, "axes.edgecolor": INK, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.linewidth": 0.8, "xtick.direction": "out", "ytick.direction": "out",
    "font.size": 8, "axes.titlesize": 9, "legend.frameon": False,
})

conf = json.load(open(os.path.join(DATA, "buffer_confirm_report.json")))
boot = json.load(open(os.path.join(DATA, "buffer_bootstrap_report.json")))
fron = json.load(open(os.path.join(DATA, "buffer_frontiers.json")))
g3 = json.load(open(os.path.join(DATA, "gate3_report.json")))["per_target"]

def save(fig, name):
    base = os.path.join(OUT, name)
    fig.savefig(base + ".pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(base + ".png", dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", name)


def margin_band(ax, lo=None, hi=None, label=None, margin=MARGIN):
    lo = -margin if lo is None else lo
    hi = margin if hi is None else hi
    ax.axhspan(lo, hi, color=HAIR, zorder=0, label=label)


def _frontiers(ax):
    """Panel (a): the four policy frontiers with both model-defined ceilings marked."""
    # (line ink, marker fill) per policy. The candidate takes the navy so the eye lands on it.
    style = {
        "SAA": ("empirical quantile policy", TEAL_INK, TEAL, "o", "-"),
        "DRO": ("Wasserstein service policy", NAVY_INK, NAVY, "D", "-"),
        "SAAbuf": ("quantile-plus-cushion policy", MTEAL_INK, MTEAL, "s", (0, (4, 2))),
        "FixedDays": ("fixed-days policy", LGREY_INK, LGREY, "^", (0, (1.6, 1.6))),
    }
    for key, (lab, ink, fill, mk, ls) in style.items():
        pts = sorted({(round(p[1], 4), p[2]) for p in fron[key]})
        x = [p[0] for p in pts]; y = [p[1] for p in pts]
        ax.plot(x, y, ls=ls, marker=mk, ms=4.8, mew=0.7, lw=1.3, color=ink,
                markerfacecolor=fill, markeredgecolor=EDGE, label=lab, zorder=3)
    for xv, lab, col, ytxt, ha in [
            (54.75, "empirical quantile policy\nceiling 54.75 d", TEAL_INK, 0.0163, "right"),
            (58.80, "Wasserstein service policy\nceiling 58.80 d", NAVY_INK, 0.0128, "left")]:
        ax.axvline(xv, ymin=0.0, ymax=0.80, color=col, lw=0.9, ls=(0, (2, 2)), zorder=2)
        ax.annotate(lab, xy=(xv, ytxt), xytext=(xv + (-0.5 if ha == "right" else 0.5), ytxt),
                    fontsize=6.4, color=col, ha=ha, va="center")
    _lo, _hi = ax.get_ylim()
    ax.set_ylim(_lo, _hi + 0.24 * (_hi - _lo))
    ax.annotate("targets beyond that ceiling are set by the ambiguity-set geometry:\n"
                "at N = 48 the sample maximum is only a 91.5% confidence 0.95-content bound",
                xy=(0.985, 0.985), xycoords="axes fraction", ha="right", va="top",
                fontsize=6.4, color=MGRY)
    ax.set_xlabel("pooled mean target (days of cover)")
    ax.set_ylabel("expected shortfall\n(mean-demand units)")
    ax.set_title("(a) Service-inventory frontiers and model-defined ceilings",
                 loc="left", fontweight="bold", fontsize=8.6)
    ax.legend(loc="lower left", fontsize=6.6, handletextpad=0.5, labelspacing=0.35)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _matched(axes):
    """Panel (b): matched-inventory paired differences, one axes per regime."""
    regs = [("pooled", "pooled"), ("maint", "maintenance regime"), ("build", "pile-build regime")]
    comps = [("DRO-SAAbuf", "versus quantile-plus-cushion policy", NAVY_INK, NAVY, "D"),
             ("DRO-FixedDays", "versus fixed-days policy", MTEAL_INK, MTEAL, "^")]
    for ax, (rk, rlab) in zip(axes, regs):
        margin_band(ax)
        for ci, (ck, clab, ink, fill, mk) in enumerate(comps):
            per = boot["primary_ES"][ck][rk]["perL"]
            Ls = sorted(per, key=lambda x: int(x))
            x = [int(L) + (ci - 0.5) * 0.22 for L in Ls]
            y = [per[L]["point"] for L in Ls]
            lo = [per[L]["point"] - per[L]["sim"][0] for L in Ls]
            hi = [per[L]["sim"][1] - per[L]["point"] for L in Ls]
            ax.errorbar(x, y, yerr=[lo, hi], fmt=mk, ms=4.8, mew=0.7, ecolor=ink,
                        markerfacecolor=fill, markeredgecolor=EDGE, color=ink,
                        elinewidth=1.2, capsize=2.4, zorder=3,
                        label=clab if ax is axes[0] else None)
        ax.axhline(0, color=INK, lw=1.0, zorder=4)
        ax.set_title(rlab, loc="left", fontsize=7.8, fontweight="bold")
        ax.set_xlabel("matched pooled mean target (days)")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("expected shortfall (mean-demand units),\n"
                       "Wasserstein service policy minus comparator")
    h, l = axes[0].get_legend_handles_labels()
    h.append(Patch(facecolor=HAIR))
    l.append("equivalence margin, plus or minus 0.005 mean-demand units")
    return h, l


# Figure 2 is unchanged from the previous build. It is inlined rather than imported so that
# one script produces every data figure and no figure depends on a file that will be retired.
def fig2():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.9),
                                  gridspec_kw=dict(width_ratios=[1.55, 1.0], wspace=0.32))
    cells = conf["cells"]; dR = conf["dR"]; sd = conf["sd_dR"]; crit = conf["crit"]
    Ns = [24, 48, 96]; rs = [0.0, 0.10, 0.25]
    # The whisker takes the ink and the marker face the fill, so the pale series stay visible.
    cols = {0.0: LGREY, 0.10: TEAL, 0.25: NAVY}
    inks = {0.0: LGREY_INK, 0.10: TEAL_INK, 0.25: NAVY_INK}
    mks = {0.0: "o", 0.10: "s", 0.25: "D"}
    margin_band(ax, label="equivalence margin", margin=RELIABILITY_MARGIN_PP)
    for r in rs:
        xs, ys, es = [], [], []
        for k, (rr, N) in enumerate(cells):
            if rr == r:
                xs.append(Ns.index(N)); ys.append(dR[k]); es.append(crit * sd[k])
        off = (rs.index(r) - 1) * 0.16
        ax.errorbar([x + off for x in xs], ys, yerr=es, fmt=mks[r], ms=6.8, mew=0.8,
                    color=inks[r], ecolor=inks[r], markerfacecolor=cols[r],
                    markeredgecolor=EDGE, elinewidth=1.5, capsize=3.2, zorder=3,
                    label=f"instability r = {r:g}")
    ax.axhline(0, color=INK, lw=1.0, zorder=4)
    ax.set_xticks(range(3)); ax.set_xticklabels([f"N = {n}" for n in Ns])
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylabel("worst-decile service excess (probability points),\nWasserstein service policy minus uniform cushion")
    ax.set_title("a   matched-inventory difference, all nine cells", loc="left", fontweight="bold")
    ax.text(0.02, 0.95, "candidate worse", transform=ax.transAxes, va="top", fontsize=7.2,
            color=MGRY)
    ax.legend(loc="upper right", fontsize=7.0, handletextpad=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # panel b: added-variable plot. The reported slope comes from a regression with window
    # fixed effects, so both variables are residualised on those dummies here; the drawn slope
    # is then exactly the reported beta_P rather than a bivariate approximation of it.
    Pv = np.array(conf["PTH"]); D = np.array(dR)
    Nd = np.array([[1.0, 1.0 if N == 48 else 0.0, 1.0 if N == 96 else 0.0] for _, N in cells])
    def resid(y):
        beta, *_ = np.linalg.lstsq(Nd, y, rcond=None)
        return y - Nd @ beta
    Pr, Dr = resid(Pv), resid(D)
    for k, (rr, N) in enumerate(cells):
        ax2.plot(Pr[k], Dr[k], mks[rr], ms=6.8, markerfacecolor=cols[rr],
                 markeredgecolor=EDGE, mew=0.8, zorder=3)
    slope = float(np.sum(Pr * Dr) / np.sum(Pr * Pr))
    xx = np.linspace(Pr.min(), Pr.max(), 20)
    ax2.plot(xx, slope * xx, color=MGRY, lw=1.3, ls=(0, (3, 2)), zorder=2)
    ax2.axhline(0, color=LGRY, lw=0.7, zorder=1)
    ax2.set_xlabel("mean panel PTH screen,\nresidual of window fixed effects")
    ax2.set_ylabel("difference (probability points),\nsame residual")
    ax2.set_title("b   screen slope, correct sign and negligible size", loc="left",
                  fontweight="bold")
    # headroom above the data so the annotation cannot sit on a marker
    _lo, _hi = ax2.get_ylim()
    ax2.set_ylim(_lo, _hi + 0.42 * (_hi - _lo))
    span = conf["PTH_range"]; eff = conf["betaP"] * span
    ax2.annotate(f"slope {slope:.1f}, one-sided 95% upper {conf['betaP_upper']:.1f}\n"
                 f"change over the whole observed span: {eff:+.4f}",
                 xy=(0.97, 0.97), xycoords="axes fraction", ha="right", va="top",
                 fontsize=6.9, color=MGRY)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    save(fig, "fig2_controlled_bands")


def fig3():
    """Figure 3: both panels of the field study's Gate 4."""
    fig = plt.figure(figsize=(7.2, 5.9))
    gs = GridSpec(2, 3, figure=fig, height_ratios=[1.18, 1.0], hspace=0.62, wspace=0.14)
    _frontiers(fig.add_subplot(gs[0, :]))
    axes = [fig.add_subplot(gs[1, 0])]
    axes += [fig.add_subplot(gs[1, i], sharey=axes[0]) for i in (1, 2)]
    for ax in axes[1:]:
        plt.setp(ax.get_yticklabels(), visible=False)
    h, l = _matched(axes)
    axes[0].annotate("(b) Matched-inventory paired differences, simultaneous 95 percent bands",
                     xy=(0.0, 1.30), xycoords="axes fraction", ha="left", va="bottom",
                     fontsize=8.6, fontweight="bold", color=INK)
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=6.8, handletextpad=0.6,
               columnspacing=1.3, bbox_to_anchor=(0.5, -0.035))
    save(fig, "fig3_field_gate4")


def fig4():
    """Figure 4: Gate 5, historical support by regime. Was Figure 5."""
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    targets = ["57", "60", "63"]
    classes = [("Routine", LGREY), ("Exceptional", TEAL), ("Unsupported", NAVY)]
    width = 0.33
    xs = np.arange(len(targets))
    for gi, (gkey, glab) in enumerate([("binding_maintenance", "maintenance regime"),
                                       ("binding_pilebuild", "pile-build regime")]):
        bottom = np.zeros(len(targets))
        for ci, (cname, col) in enumerate(classes):
            nkey = "n_maintenance" if gi == 0 else "n_pilebuild"
            vals = np.array([g3[t][gkey][cname] / g3[t][nkey] * 100 for t in targets])
            ax.bar(xs + (gi - 0.5) * (width + 0.06), vals, width, bottom=bottom,
                   color=col, edgecolor="white", lw=0.6, zorder=2,
                   label=cname if gi == 0 else None)
            for xi, (v, b) in enumerate(zip(vals, bottom)):
                if v >= 9:
                    txt = f"{v:.1f}" if v > 99 else f"{v:.0f}"
                    ax.text(xs[xi] + (gi - 0.5) * (width + 0.06), b + v / 2, txt,
                            ha="center", va="center", fontsize=6.8,
                            color="white" if cname == "Unsupported" else INK, fontweight="bold")
            bottom += vals
        for xi, t in enumerate(targets):
            nn = g3[t]["n_maintenance"] if gi == 0 else g3[t]["n_pilebuild"]
            ax.text(xs[xi] + (gi - 0.5) * (width + 0.06), 101.0,
                    ("maintenance\nregime" if gi == 0 else "pile-build\nregime") + f"\nn={nn:,}",
                    ha="center", va="bottom", fontsize=6.4, color=MGRY, linespacing=1.25)
    ax.set_xticks(xs); ax.set_xticklabels([f"{t}-day target" for t in targets])
    ax.set_ylim(0, 132); ax.set_ylabel("share of cases within the regime (percent)")
    ax.set_title("Historical support by regime, own-history benchmarks", loc="left",
                 fontweight="bold")
    ax.legend(loc="lower center", fontsize=7.0, ncol=3, handletextpad=0.5, columnspacing=1.2,
              bbox_to_anchor=(0.5, -0.26))
    ax.annotate("at the 60-day target, 67.4 percent of cases in the pile-build regime would need\n"
                "more than one month at that plant's own ninetieth-percentile build rate",
                xy=(0.0, -0.40), xycoords="axes fraction", ha="left", va="top",
                fontsize=6.8, color=MGRY)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig4_regime_support")


if __name__ == "__main__":
    fig2(); fig3(); fig4()
