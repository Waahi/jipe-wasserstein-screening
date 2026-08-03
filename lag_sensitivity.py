# -*- coding: utf-8 -*-
"""Publication-lag sensitivity for the retrospective field design.

Section 6.0 evaluates under an OPERATOR-INFORMATION assumption: a plant's own contemporaneous burn and
inventory are treated as known to that plant's operator at the decision date, even though the public
record appeared 13 to 24 months later. Section 8 records that archived plant-level vintages do not exist,
so the gap between an operator's own books and the later public record cannot be measured directly.

What CAN be measured is the other end of the range: what the same comparison looks like for an analyst
restricted to the PUBLIC information set, that is with every training window ending L months before the
decision. That brackets the design. If the operational-equivalence conclusion survives at L = 13 and
L = 24, the operator-information assumption is not carrying the result.

Output: data/lag_sensitivity.json.
"""
import json, os
from collections import defaultdict
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(D, "data")
# The derived monthly coal panel ships with the deposit. It was built from the public
# EIA-923 workbooks by analysis/build_panel.py; digests are in analysis/eia923_hashes.json.
SP = os.path.join(D, "analysis")
ALPHA, WIN = 0.05, 48
LAGS = [0, 13, 24]
EPS_GRID = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20]
CUSHION_GRID = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]


def q_inv(Z, a):
    return float(np.quantile(Z, 1 - a, method="inverted_cdf"))


def wc_prob_exceed(Z, k, eps):
    S = len(Z); base = float(np.mean(Z > k))
    below = np.sort(k - Z[Z <= k]); budget = eps; extra = 0.0
    for gap in below:
        c = gap / S
        if c <= budget:
            budget -= c; extra += 1.0 / S
        else:
            if gap > 0:
                extra += (budget / (gap / S)) * (1.0 / S)
            break
    return base + extra


def dro_k(Z, a, eps):
    lo, hi = 0.0, float(max(0.0, np.max(Z))) + 1.0
    if wc_prob_exceed(Z, lo, eps) <= a:
        return 0.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if wc_prob_exceed(Z, mid, eps) <= a:
            hi = mid
        else:
            lo = mid
    return hi


raw = json.load(open(os.path.join(SP, "coal_panel_2015_2024.json")))
P = defaultdict(dict)
for kk, v in raw.items():
    p, y, m = kk.split("|")
    if v.get("burn") and v["burn"] > 0:
        P[p][(int(y), int(m))] = float(v["burn"])

months = sorted({ym for d in P.values() for ym in d})
idx = {ym: i for i, ym in enumerate(months)}
T = len(months)
print(f"panel: {len(P)} plants, {T} months from {months[0]} to {months[-1]}")

# outer origins: the last 35 decision months for which a target month exists
origins = list(range(T - 36, T - 1))
print(f"outer origins: {len(origins)}")

res = {}
for L in LAGS:
    # inner calibration of the radius, on origins strictly before the evaluation block
    inner = list(range(T - 36 - 12, T - 36))
    best_eps, best_gap = 0.0, None
    for eps in EPS_GRID:
        viol = []
        for p, dd in P.items():
            for t0 in inner:
                tr = [months[j] for j in range(t0 - WIN - L + 1, t0 - L + 1) if j >= 0]
                w = np.array([dd[ym] for ym in tr if ym in dd], float)
                tgt = months[t0 + 1]
                if len(w) < 24 or tgt not in dd:
                    continue
                mb = w.mean()
                if mb <= 0:
                    continue
                Z = w / mb
                viol.append(1.0 if dd[tgt] / mb > dro_k(Z, ALPHA, eps) else 0.0)
        if not viol:
            continue
        gap = abs(float(np.mean(viol)) - ALPHA)
        if best_gap is None or gap < best_gap:
            best_gap, best_eps = gap, eps

    # evaluation: paired shortfall at matched pooled mean inventory
    per_origin = []
    for t0 in origins:
        rows = []
        for p, dd in P.items():
            tr = [months[j] for j in range(t0 - WIN - L + 1, t0 - L + 1) if j >= 0]
            w = np.array([dd[ym] for ym in tr if ym in dd], float)
            tgt = months[t0 + 1]
            if len(w) < 24 or tgt not in dd:
                continue
            mb = w.mean()
            if mb <= 0:
                continue
            Z, tv = w / mb, dd[tgt] / mb
            rows.append((Z, tv))
        if len(rows) < 20:
            continue
        kd = np.array([dro_k(Z, ALPHA, best_eps) for Z, _ in rows])
        inv_d = kd.mean()
        # quantile-plus-cushion matched to the candidate's pooled mean inventory
        best_c, best_d = None, None
        for c in CUSHION_GRID:
            ks = np.array([q_inv(Z, ALPHA) + c for Z, _ in rows])
            d = abs(ks.mean() - inv_d)
            if best_d is None or d < best_d:
                best_d, best_c = d, c
        ks = np.array([q_inv(Z, ALPHA) + best_c for Z, _ in rows])
        tv = np.array([t for _, t in rows])
        sh_d = np.maximum(0.0, tv - kd).mean()
        sh_s = np.maximum(0.0, tv - ks).mean()
        per_origin.append(dict(diff=float(sh_d - sh_s), inv_d=float(inv_d),
                               inv_s=float(ks.mean()), cushion=best_c, n=len(rows)))

    d = np.array([r["diff"] for r in per_origin])
    rng = np.random.default_rng(20260727)
    n = len(d)
    bs = np.array([d[rng.integers(0, n, n)].mean() for _ in range(6000)])
    res[str(L)] = dict(lag_months=L, radius=best_eps, n_origins=n,
                       mean_diff=float(d.mean()),
                       ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                       mean_inventory_candidate=float(np.mean([r["inv_d"] for r in per_origin])),
                       mean_inventory_comparator=float(np.mean([r["inv_s"] for r in per_origin])))
    r = res[str(L)]
    print(f"L={L:2d} months | radius {best_eps} | {n} origins | "
          f"diff {r['mean_diff']:+.4f} [{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}] | "
          f"inventory {r['mean_inventory_candidate']:.3f} vs {r['mean_inventory_comparator']:.3f}")

json.dump(res, open(os.path.join(DATA, "lag_sensitivity.json"), "w"), indent=2)
print("\nwrote data/lag_sensitivity.json")
