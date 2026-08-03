# -*- coding: utf-8 -*-
"""Measure what each gate actually costs, on the real coal panel with the real operator.

Section 8.3 argues the gates are ordered by cost. Until now it gave no figures. This script
supplies them by timing the same computations the studies ran, on the same data, so the ordering
claim is measured rather than asserted.

Output: data/gate_cost.json, consumed by make_numbers.py.
"""
import json, os, time
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(D, "data")
ALPHA = 0.05
WIN = 48
rng = np.random.default_rng(20260727)


def q_inv(Z, a):
    return float(np.quantile(Z, 1 - a, method="inverted_cdf"))


def wc_prob_exceed(Z, k, eps):
    """Corrected operator: fractional final atom. Same routine the studies used."""
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


def dro_k(Z, a, eps):
    lo, hi = 0.0, float(max(0.0, np.max(Z))) + 1.0
    if wc_prob_exceed(Z, lo, eps) <= a:
        return 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if wc_prob_exceed(Z, mid, eps) <= a:
            hi = mid
        else:
            lo = mid
    return hi


def pth(Zs, alpha=ALPHA, KB=4):
    """Definition 1 on one panel: K blocks of inner origins, adjacent-block cross-unit covariance."""
    I = len(Zs)
    gik = np.full((I, KB), np.nan)
    for i, Z in enumerate(Zs):
        blocks = np.array_split(np.arange(len(Z) - 12, len(Z)), KB)
        for kb, blk in enumerate(blocks):
            vv = []
            for t in blk:
                w = Z[max(0, t - WIN):t]
                if len(w) < 8:
                    continue
                vv.append(1.0 if Z[t] > q_inv(w, alpha) else 0.0)
            if vv:
                gik[i, kb] = max(0.0, float(np.mean(vv)) - alpha)
    covs = []
    for kb in range(KB - 1):
        a_, b_ = gik[:, kb], gik[:, kb + 1]
        ok = ~np.isnan(a_) & ~np.isnan(b_)
        if ok.sum() > 4:
            covs.append(float(np.cov(a_[ok], b_[ok])[0, 1]))
    return float(max(0.0, np.mean(covs))) if covs else 0.0


# ---- build a representative panel from the real coal series ----
# The derived monthly coal panel ships with the deposit. It was built from the public
# EIA-923 workbooks by analysis/build_panel.py; digests are in analysis/eia923_hashes.json.
SP = os.path.join(D, "analysis")
raw = json.load(open(os.path.join(SP, "coal_panel_2015_2024.json")))
from collections import defaultdict
P = defaultdict(list)
for kk, v in raw.items():
    p, y, m = kk.split("|")
    if v.get("burn") and v["burn"] > 0:
        P[p].append((int(y), int(m), float(v["burn"])))
series = []
for p, seq in P.items():
    seq.sort()
    b = np.array([x[2] for x in seq], float)
    if len(b) >= WIN + 12:
        mb = b[:WIN].mean()
        if mb > 0:
            series.append(b / mb)
series = series[:60]
N_UNITS = len(series)
print(f"panel: {N_UNITS} units from the real coal record")


def bench(fn, reps):
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t0) / reps


Z0 = series[0][:WIN]

# Gate 1: the structural inspection. One worst-case evaluation at two radii is enough to see
# whether the cost form moves; the check itself is a comparison of two scalars.
g1 = bench(lambda: (wc_prob_exceed(Z0, q_inv(Z0, ALPHA), 0.0),
                    wc_prob_exceed(Z0, q_inv(Z0, ALPHA), 0.2)), 200)

# Gate 2: the screen, one pass over the training window for the whole panel.
g2 = bench(lambda: pth(series), 3)

# Gate 3: one evaluation of the uniform cushion against the service target, whole panel.
def g3_once():
    for Z in series:
        w = Z[:WIN]
        q = q_inv(w, ALPHA)
        _ = float(np.mean(Z[WIN:WIN + 12] > q + 0.05))
g3 = bench(g3_once, 20)

# Gate 4: the candidate must be solved at every decision point, then the paired comparison
# bootstrapped. Time one radius calibration plus one solve per unit, then scale the bootstrap.
def g4_solve_once():
    for Z in series:
        w = Z[:WIN]
        _ = dro_k(w, ALPHA, 0.05)
g4_solve = bench(g4_solve_once, 3)

B = 6000
t0 = time.perf_counter()
X = np.array([[float(np.mean(Z[WIN:WIN + 12])) for Z in series]])
for _ in range(200):
    idx = rng.integers(0, N_UNITS, N_UNITS)
    _ = X[0][idx].mean()
boot_unit = (time.perf_counter() - t0) / 200
g4 = g4_solve + boot_unit * B

out = dict(units=N_UNITS, window=WIN, alpha=ALPHA, bootstrap_resamples=B,
           gate1_seconds=g1, gate2_seconds=g2, gate3_seconds=g3,
           gate4_solve_seconds=g4_solve, gate4_total_seconds=g4,
           ratio_g4_over_g1=g4 / g1 if g1 else None,
           ratio_g4_over_g2=g4 / g2 if g2 else None,
           ratio_g4_over_g3=g4 / g3 if g3 else None)
json.dump(out, open(os.path.join(DATA, "gate_cost.json"), "w"), indent=2)
for k, v in out.items():
    print(f"{k:26s} {v}")
