# -*- coding: utf-8 -*-
"""RETIRED. Superseded by figs_data.py for the six-section build.

Kept for provenance only: it produced Figures 2 to 5 of the nine-section draft. The six-section
paper carries four figures, with the two that reported Gate 4 of the field study merged. Do not run
this file; its outputs would reintroduce figure numbers the manuscript no longer uses.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

OUT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."), "data")

BLUE = "#0072B2"; ORANGE = "#E69F00"; GREEN = "#009E73"; VERM = "#D55E00"; SKY = "#56B4E9"
INK = "#222222"; MGRY = "#666666"; LGRY = "#CCCCCC"; HAIR = "#E3E7EB"
# two different quantities happen to share the numeral; keep the dimensions apart
RELIABILITY_MARGIN_PP = 0.005   # probability points, worst-decile service excess
SHORTFALL_MARGIN_MDU = 0.005   # mean-demand units, expected shortfall
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


# ---------------------------------------------------------------- Figure 2
def fig2():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.9),
                                  gridspec_kw=dict(width_ratios=[1.55, 1.0], wspace=0.32))
    cells = conf["cells"]; dR = conf["dR"]; sd = conf["sd_dR"]; crit = conf["crit"]
    Ns = [24, 48, 96]; rs = [0.0, 0.10, 0.25]
    cols = {0.0: BLUE, 0.10: ORANGE, 0.25: VERM}
    mks = {0.0: "o", 0.10: "s", 0.25: "D"}
    margin_band(ax, label="equivalence margin", margin=RELIABILITY_MARGIN_PP)
    for r in rs:
        xs, ys, es = [], [], []
        for k, (rr, N) in enumerate(cells):
            if rr == r:
                xs.append(Ns.index(N)); ys.append(dR[k]); es.append(crit * sd[k])
        off = (rs.index(r) - 1) * 0.16
        ax.errorbar([x + off for x in xs], ys, yerr=es, fmt=mks[r], ms=6.5, mew=0.9,
                    color=cols[r], ecolor=cols[r], elinewidth=1.5, capsize=3.2, zorder=3,
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
        ax2.plot(Pr[k], Dr[k], mks[rr], ms=6.5, color=cols[rr], mew=0.9, zorder=3)
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


# ---------------------------------------------------------------- Figure 3
def fig3():
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    style = {
        "SAA": ("empirical quantile policy", BLUE, "o", "-"),
        "DRO": ("Wasserstein service policy", VERM, "D", "-"),
        "SAAbuf": ("quantile-plus-cushion policy", GREEN, "s", (0, (4, 2))),
        "FixedDays": ("fixed-days policy", MGRY, "^", (0, (1.6, 1.6))),
    }
    for key, (lab, col, mk, ls) in style.items():
        pts = sorted({(round(p[1], 4), p[2]) for p in fron[key]})
        x = [p[0] for p in pts]; y = [p[1] for p in pts]
        ax.plot(x, y, ls=ls, marker=mk, ms=5.2, mew=0.8, lw=1.4, color=col, label=lab, zorder=3)
    for xv, lab, col, ytxt, ha in [
            (54.75, "empirical quantile policy\nceiling 54.75 d", BLUE, 0.0163, "right"),
            (58.80, "Wasserstein service policy\nceiling 58.80 d", VERM, 0.0128, "left")]:
        ax.axvline(xv, ymin=0.0, ymax=0.80, color=col, lw=0.9, ls=(0, (2, 2)), zorder=2)
        ax.annotate(lab, xy=(xv, ytxt), xytext=(xv + (-0.5 if ha == "right" else 0.5), ytxt),
                    fontsize=6.8, color=col, ha=ha, va="center")
    _lo, _hi = ax.get_ylim()
    ax.set_ylim(_lo, _hi + 0.22 * (_hi - _lo))
    ax.annotate("targets beyond that ceiling are set by the\n"
                "ambiguity-set geometry: at N = 48 the sample maximum is\n"
                "only a 91.5% confidence 0.95-content bound",
                xy=(0.985, 0.985), xycoords="axes fraction", ha="right", va="top",
                fontsize=6.8, color=MGRY)
    ax.set_xlabel("pooled mean target (days of cover)")
    ax.set_ylabel("expected shortfall (mean-demand units)")
    ax.set_title("Service-inventory frontiers and model-defined ceilings", loc="left",
                 fontweight="bold")
    ax.legend(loc="lower left", fontsize=7.0, handletextpad=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig3_frontiers_ceilings")


# ---------------------------------------------------------------- Figure 4
def fig4():
    regs = [("pooled", "pooled"), ("maint", "maintenance regime"), ("build", "pile-build regime")]
    comps = [("DRO-SAAbuf", "versus quantile-plus-cushion policy", VERM, "D"),
             ("DRO-FixedDays", "versus fixed-days policy", MGRY, "^")]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True,
                             gridspec_kw=dict(wspace=0.12))
    for ax, (rk, rlab) in zip(axes, regs):
        margin_band(ax)
        for ci, (ck, clab, col, mk) in enumerate(comps):
            per = boot["primary_ES"][ck][rk]["perL"]
            Ls = sorted(per, key=lambda x: int(x))
            x = [int(L) + (ci - 0.5) * 0.22 for L in Ls]
            y = [per[L]["point"] for L in Ls]
            lo = [per[L]["point"] - per[L]["sim"][0] for L in Ls]
            hi = [per[L]["sim"][1] - per[L]["point"] for L in Ls]
            ax.errorbar(x, y, yerr=[lo, hi], fmt=mk, ms=5.2, mew=0.8, color=col, ecolor=col,
                        elinewidth=1.3, capsize=2.6, zorder=3,
                        label=clab if ax is axes[0] else None)
        ax.axhline(0, color=INK, lw=1.0, zorder=4)
        ax.set_title(rlab, loc="left", fontsize=8.2, fontweight="bold")
        ax.set_xlabel("matched pooled mean target (days)")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("expected shortfall (mean-demand units),\nWasserstein service policy minus comparator")
    h, l = axes[0].get_legend_handles_labels()
    h.append(Patch(facecolor=HAIR)); l.append("equivalence margin, plus or minus 0.005 mean-demand units")
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=7.0, handletextpad=0.6,
               columnspacing=1.4, bbox_to_anchor=(0.5, -0.26))
    fig.suptitle("Matched-inventory paired differences, simultaneous 95 per cent bands",
                 x=0.005, ha="left", fontweight="bold", fontsize=9)
    save(fig, "fig4_matched_bands")


# ---------------------------------------------------------------- Figure 5
def fig5():
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    targets = ["57", "60", "63"]
    classes = [("Routine", GREEN), ("Exceptional", ORANGE), ("Unsupported", VERM)]
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
                    # one decimal above 99 so the label cannot read as an exact 100
                    txt = f"{v:.1f}" if v > 99 else f"{v:.0f}"
                    ax.text(xs[xi] + (gi - 0.5) * (width + 0.06), b + v / 2, txt,
                            ha="center", va="center", fontsize=6.8,
                            color="white" if cname != "Exceptional" else INK, fontweight="bold")
            bottom += vals
        for xi, t in enumerate(targets):
            nn = g3[t]["n_maintenance"] if gi == 0 else g3[t]["n_pilebuild"]
            ax.text(xs[xi] + (gi - 0.5) * (width + 0.06), 101.0,
                    ("maintenance\nregime" if gi == 0 else "pile-build\nregime") + f"\nn={nn:,}",
                    ha="center", va="bottom", fontsize=6.4, color=MGRY, linespacing=1.25)
    ax.set_xticks(xs); ax.set_xticklabels([f"{t}-day target" for t in targets])
    ax.set_ylim(0, 132); ax.set_ylabel("share of cases within the regime (per cent)")
    ax.set_title("Historical support by regime, own-history benchmarks", loc="left",
                 fontweight="bold")
    ax.legend(loc="lower center", fontsize=7.0, ncol=3, handletextpad=0.5, columnspacing=1.2,
              bbox_to_anchor=(0.5, -0.26))
    ax.annotate("at the 60-day target, 67.4 per cent of cases in the pile-build regime would need\n"
                "more than one month at that plant's own ninetieth-percentile build rate",
                xy=(0.0, -0.40), xycoords="axes fraction", ha="left", va="top",
                fontsize=6.8, color=MGRY)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig5_regime_support")


if __name__ == "__main__":
    fig2(); fig3(); fig4(); fig5()
