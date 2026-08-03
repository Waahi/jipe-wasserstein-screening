# -*- coding: utf-8 -*-
"""Appendix B evidence: 400-case independent LP verification of the worst-case exceedance operator.

Worst-case P(Z > k) over a type-1 Wasserstein ball of radius eps, as a transport LP:
    max   base + sum_{i: z_i <= k} x_i / S
    s.t.  sum_{i: z_i <= k} x_i (k - z_i) / S <= eps,   0 <= x_i <= 1
The LP permits fractional transport. The original operator moved whole atoms only; the corrected
operator moves a fractional final atom. This script compares BOTH against the LP over a fixed,
seeded case set, and reports the maximum absolute discrepancy of each.

Deterministic regression cases are included by construction: eps = 0, a budget ample enough to reach
probability one, all mass at the threshold, and a case whose budget lands strictly inside an atom so
the fractional move is the binding difference.
"""
import json
import numpy as np
from scipy.optimize import linprog

SEED = 20260726
TOL = 1e-9


def wc_whole(Z, k, eps):
    S = len(Z); base = float(np.mean(Z > k))
    below = np.sort(k - Z[Z <= k]); budget = eps; moved = 0
    for gap in below:
        cost = gap / S
        if cost <= budget:
            budget -= cost; moved += 1
        else:
            break
    return base + moved / S


def wc_frac(Z, k, eps):
    S = len(Z); base = float(np.mean(Z > k))
    below = np.sort(k - Z[Z <= k]); budget = eps; extra = 0.0
    for gap in below:
        cost = gap / S
        if cost <= budget:
            budget -= cost; extra += 1.0 / S
        else:
            if gap > 0:
                extra += (budget / (gap / S)) * (1.0 / S)
            budget = 0.0
            break
    return base + extra


def wc_lp(Z, k, eps):
    Z = np.asarray(Z, float); S = len(Z)
    base = float(np.mean(Z > k))
    idx = np.where(Z <= k)[0]
    if len(idx) == 0:
        return base
    gaps = (k - Z[idx]) / S
    c = -np.ones(len(idx)) / S
    res = linprog(c, A_ub=[gaps], b_ub=[eps], bounds=[(0, 1)] * len(idx), method="highs")
    if not res.success:
        return float("nan")
    return base + (-res.fun)


rng = np.random.RandomState(SEED)


def draw(family, n):
    if family == "exponential":
        return np.round(rng.exponential(1.0, n), 3)
    if family == "uniform":
        return np.round(rng.uniform(0.0, 3.0, n), 3)
    if family == "lognormal":
        return np.round(rng.lognormal(0.0, 0.6, n), 3)
    if family == "integer":                      # heavy ties by construction
        return rng.randint(0, 5, n).astype(float)
    if family == "coarse":                       # ties on a 0.5 grid
        return np.round(rng.uniform(0.0, 4.0, n) * 2.0) / 2.0
    raise ValueError(family)


FAMILIES = ["exponential", "uniform", "lognormal", "integer", "coarse"]
rows = []

# ---- deterministic regression cases, 4 of them ----
Zt = np.array([1.0] * 10)
rows.append(("regression: all mass at threshold", Zt, 1.0, 0.10))
Zr = np.array([0.0, 0.0, 0.0, 0.0, 2.0])
rows.append(("regression: eps zero", Zr, 1.0, 0.0))
rows.append(("regression: budget ample for prob one", Zr, 1.0, 10.0))
# budget lands strictly inside the first atom: gap 1.0, S 5, so cost 0.2; give 0.1
rows.append(("regression: fractional final atom", Zr, 1.0, 0.10))

# ---- randomised cases, filling to 400 total ----
while len(rows) < 400:
    fam = FAMILIES[len(rows) % len(FAMILIES)]
    n = int(rng.randint(8, 41))
    Z = draw(fam, n)
    q = float(rng.uniform(30.0, 90.0))
    k = float(np.percentile(Z, q))
    eps = float(rng.choice([0.0, 0.01, 0.03, 0.10, 0.25, 0.60, 2.00]))
    rows.append((f"{fam} n={n} q={q:.0f}", Z, k, eps))

max_whole = 0.0
max_frac = 0.0
worst_whole = worst_frac = None
n_frac_binding = 0
n_eps_zero = 0
for name, Z, k, eps in rows:
    g = wc_whole(Z, k, eps)
    f = wc_frac(Z, k, eps)
    lp = wc_lp(Z, k, eps)
    dg, df = abs(g - lp), abs(f - lp)
    if dg > max_whole:
        max_whole, worst_whole = dg, (name, k, eps, g, lp)
    if df > max_frac:
        max_frac, worst_frac = df, (name, k, eps, f, lp)
    if dg > TOL:
        n_frac_binding += 1
    if eps == 0.0:
        n_eps_zero += 1

out = dict(seed=SEED, tolerance=TOL, n_cases=len(rows),
           n_eps_zero=n_eps_zero, n_where_whole_atom_differs=n_frac_binding,
           max_abs_whole_minus_lp=max_whole, max_abs_frac_minus_lp=max_frac,
           worst_whole=worst_whole and dict(case=worst_whole[0], k=worst_whole[1],
                                            eps=worst_whole[2], op=worst_whole[3], lp=worst_whole[4]),
           families=FAMILIES, n_range=[8, 40],
           eps_grid=[0.0, 0.01, 0.03, 0.10, 0.25, 0.60, 2.00],
           percentile_range=[30, 90])
print(json.dumps(out, indent=2, default=float))
import os
_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "operator_lp400.json")
with open(_out, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, default=float)
