# -*- coding: utf-8 -*-
"""Positive control, implemented to STEP5J_POSITIVE_CONTROL_FROZEN.md.

Run order is mandatory and enforced by the CLI:
    python poscontrol.py calib   -> stream 1, threshold tau, writes tau.json
    python poscontrol.py confirm -> streams 2 and 3, refuses to run without tau.json

DGP (frozen): Y_it = exp(sigma_i Z_it - sigma_i^2/2), mean one, unit type fixed for the whole panel,
30 low and 30 high per panel. Standardising mean uses the PRECEDING window only.
PTH depends only on the empirical-quantile policy, so it is budget-independent; the null configurations
screened are therefore the three windows.
"""
import sys, os, json, time
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
ALPHA = 0.05
I_LOW = I_HIGH = 30
I_UNITS = I_LOW + I_HIGH
K_INNER, K_OUTER, KB = 12, 12, 4
WINDOWS = (24, 48, 96)
SIGMA = {"null": (0.35, 0.35), "moderate": (0.25, 0.45), "large": (0.15, 0.55)}
BUDGETS = {"tight": 1.740, "moderate": 1.936, "generous": 2.252}   # frozen order-up-to levels
SEED_CALIB, SEED_NULL, SEED_VALUE = 700_001, 800_002, 900_003      # three independent streams
CALIB_REPS = 20_000
DELTA_R, DELTA_S = 0.010, 0.005                                     # probability points / mean-demand


def gen(sig_lo, sig_hi, N, rng, scramble=False):
    """Return standardised-demand matrix D (I x T) and the evaluation-block type labels."""
    T = N + K_INNER + K_OUTER
    sig = np.concatenate([np.full(I_LOW, sig_lo), np.full(I_HIGH, sig_hi)])
    Z = rng.standard_normal((I_UNITS, T))
    D = np.exp(sig[:, None] * Z - (sig[:, None] ** 2) / 2.0)
    if scramble:
        # persistence-destruction placebo: same innovations, same 30/30 split, same pooled marginal
        # and same budget, but the evaluation block's tail identities are re-drawn independently of
        # the identities the history reveals.
        perm = rng.permutation(I_UNITS)
        ev = slice(N + K_INNER, T)
        D[:, ev] = D[perm][:, ev]
    return D


def _origin_stats(D, N, t):
    """empirical (1-alpha) quantile of standardised demand on the preceding window, and the test value."""
    win = D[:, t - N:t]
    m = win.mean(axis=1)
    Zw = win / m[:, None]
    q = np.quantile(Zw, 1 - ALPHA, axis=1, method="inverted_cdf")
    return q, D[:, t] / m, m


def pth(D, N):
    """Persistence screen: adjacent-block cross-unit covariance of per-unit service deficits."""
    inner = np.arange(N, N + K_INNER)
    blocks = np.array_split(inner, KB)
    g = np.empty((I_UNITS, KB))
    for k, blk in enumerate(blocks):
        v = np.zeros(I_UNITS)
        for t in blk:
            q, test, _ = _origin_stats(D, N, t)
            v += (test > q)
        g[:, k] = np.maximum(0.0, v / len(blk) - ALPHA)
    covs = [np.cov(g[:, k], g[:, k + 1])[0, 1] for k in range(KB - 1)]
    return float(max(0.0, float(np.mean(covs))))


# ---------------------------------------------------------------- stream 1: threshold
def calibrate(reps=CALIB_REPS):
    rng = np.random.default_rng(SEED_CALIB)
    lo, hi = SIGMA["null"]
    maxima = np.empty(reps)
    t0 = time.time()
    for r in range(reps):
        # replication-level maximum across the null configurations screened (the three windows)
        maxima[r] = max(pth(gen(lo, hi, N, rng), N) for N in WINDOWS)
        if r and r % 2000 == 0:
            el = time.time() - t0
            print(f"  {r}/{reps}  {el:.0f}s elapsed, ~{el/r*(reps-r):.0f}s left", flush=True)
    tau = float(np.percentile(maxima, 95))
    rec = dict(tau=tau, reps=reps, rule="95th percentile of the replication-level maximum PTH "
                                         "across the three null windows",
               seed_stream=SEED_CALIB, windows=list(WINDOWS), sigma_null=list(SIGMA["null"]),
               mean_max=float(maxima.mean()), median_max=float(np.median(maxima)),
               p99_max=float(np.percentile(maxima, 99)),
               mc_se_of_p95=float(np.std(maxima, ddof=1) / np.sqrt(reps)))
    json.dump(rec, open(os.path.join(OUT, "tau.json"), "w"), indent=1)
    print(f"\nFROZEN THRESHOLD tau = {tau:.6f}")
    print(f"  from {reps} replications, mean of maxima {rec['mean_max']:.6f}, "
          f"median {rec['median_max']:.6f}, 99th {rec['p99_max']:.6f}")
    print("  written to tau.json; record it into STEP5J before any value cell is run")


# ---------------------------------------------------------------- manipulation check only
def screen_cells(reps, seed, levels, tag):
    """Report PTH per (heterogeneity level, window) for the given stream. No policy evaluation."""
    rng = np.random.default_rng(seed)
    out = {}
    for lev in levels:
        lo, hi = SIGMA[lev]
        for N in WINDOWS:
            vals = np.array([pth(gen(lo, hi, N, rng), N) for _ in range(reps)])
            out[f"{lev}|N{N}"] = dict(mean=float(vals.mean()), median=float(np.median(vals)),
                                      p05=float(np.percentile(vals, 5)),
                                      p95=float(np.percentile(vals, 95)), n=int(reps))
            print(f"  {tag} {lev:9s} N={N:<3} PTH mean {vals.mean():.6f}  "
                  f"median {np.median(vals):.6f}", flush=True)
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "help"
    if mode == "calib":
        calibrate(int(sys.argv[2]) if len(sys.argv) > 2 else CALIB_REPS)
    elif mode == "screen":
        if not os.path.exists(os.path.join(OUT, "tau.json")):
            raise SystemExit("refusing to run: tau.json missing, stream 1 must complete first")
        tau = json.load(open(os.path.join(OUT, "tau.json")))["tau"]
        print(f"frozen tau = {tau:.6f}\n")
        reps = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        res = screen_cells(reps, SEED_VALUE, ["null", "moderate", "large"], "value-stream")
        json.dump(dict(tau=tau, cells=res), open(os.path.join(OUT, "screen_check.json"), "w"), indent=1)
        print("\nmanipulation check versus frozen tau:")
        for k, v in res.items():
            print(f"  {k:16s} mean {v['mean']:.6f}  {'ABOVE tau' if v['mean'] > tau else 'below tau'}")
    else:
        print(__doc__)


# ---------------------------------------------------------------- positive control 2 (STEP5K)
BETA = {"none": 0.00000, "moderate": 0.11215, "large": 0.27455}


def gen_drift(beta, N, rng, scramble=False):
    """STEP5K DGP: sigma_it = 0.35 + s_i * beta * g_t, signs fixed, balanced 30/30."""
    T = N + K_INNER + K_OUTER
    s = np.concatenate([np.full(I_LOW, -1.0), np.full(I_HIGH, +1.0)])
    g = np.arange(T) / (T - 1.0)
    sig = 0.35 + s[:, None] * beta * g[None, :]
    eps = rng.standard_normal((I_UNITS, T))
    D = np.exp(sig * eps - (sig ** 2) / 2.0)
    if scramble:
        perm = rng.permutation(I_UNITS)
        ev = slice(N + K_INNER, T)
        D[:, ev] = D[perm][:, ev]
    return D


def screen_drift(reps, seed, tag="pc2"):
    rng = np.random.default_rng(seed)
    out = {}
    for lev, b in BETA.items():
        for N in WINDOWS:
            vals = np.array([pth(gen_drift(b, N, rng), N) for _ in range(reps)])
            out[f"{lev}|N{N}"] = float(vals.mean())
            print(f"  {tag} drift={lev:9s} N={N:<3} PTH mean {vals.mean():.6f}  "
                  f"median {np.median(vals):.6f}", flush=True)
    return out
