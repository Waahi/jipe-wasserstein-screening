# -*- coding: utf-8 -*-
"""Step 5h FROZEN service-reliability confirmatory experiment (STEP5H §9, Codex 019f93ea).
ONE run on the frozen DGP; fail -> STOP. Primary metric R = CVaR_0.90 over units of g_i=(v_i-alpha)_+,
v_i = TRUE conditional violation rate (analytic from DGP latent state). Reliability-optimized global
buffer (fair falsifier). Predictor = PTH (persistence of per-unit inner service deficit). 4-gate.
"""
import sys, numpy as np
from math import erf, sqrt, log
import backtest_v2 as bt

ALPHA = 0.05
EPSGRID = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75]
BGRID = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75]
ALPHAP = [0.02, 0.05, 0.10]          # global-buffer's own service level (reliability-optimized)
I_UNITS = 80
K_INNER = 12
K_OUTER = 12
SIGMA = 0.35
AR = 0.9
CVAR_Q = 0.90


def Phi(z): return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def gen_panel(I, T, r, rng):
    D = np.empty((I, T)); X = np.zeros((I, T))
    unstable = np.zeros(I, bool); unstable[I // 2:] = True
    mu = rng.normal(0.0, 0.3, I)
    sd_eta = r * SIGMA
    for i in range(I):
        x = 0.0
        for t in range(T):
            if unstable[i] and sd_eta > 0:
                x = AR * x + rng.normal(0.0, sd_eta)
            X[i, t] = x
            D[i, t] = np.exp(mu[i] + x + rng.normal(0.0, SIGMA))
    return D, X, mu, unstable, sd_eta


def cvar(g, q=CVAR_Q):
    g = np.sort(np.asarray(g, float))
    k = int(np.ceil(q * len(g)))
    tail = g[k:] if k < len(g) else g[-1:]
    return float(np.mean(tail)) if len(tail) else float(g[-1])


def inner_buffer(Z, alpha, bgrid):
    n = len(Z)
    if n < 16:
        return 0.0
    for b in bgrid:
        v = []
        for h in range(min(8, n // 4), 0, -1):
            fit = Z[:-h]; test = Z[-h]
            if len(fit) < 8:
                continue
            if test > bt.q_inv(fit, alpha) + b:
                v.append(1.0)
            else:
                v.append(0.0)
        if v and np.mean(v) <= alpha:
            return b
    return bgrid[-1]


def run_panel(D, X, mu, unstable, sd_eta, N):
    I, T = D.shape
    inner_os = list(range(N, N + K_INNER))
    outer_os = list(range(N + K_INNER, N + K_INNER + K_OUTER))
    sig2 = SIGMA ** 2

    # ---- PTH: per-unit inner service deficits in K sub-blocks ----
    KB = 4
    blk = np.array_split(np.array(inner_os), KB)
    gik = np.full((I, KB), np.nan)
    for i in range(I):
        for kb, blks in enumerate(blk):
            vv = []
            for t in blks:
                win = D[i, t - N:t]; m = win.mean()
                if m <= 0:
                    continue
                Z = win / m
                vv.append(1.0 if D[i, t] / m > bt.q_inv(Z, ALPHA) else 0.0)
            if vv:
                gik[i, kb] = max(0.0, np.mean(vv) - ALPHA)
    covs = []
    for kb in range(KB - 1):
        a = gik[:, kb]; b = gik[:, kb + 1]
        ok = ~np.isnan(a) & ~np.isnan(b)
        if ok.sum() > 4:
            covs.append(np.cov(a[ok], b[ok])[0, 1])
    PTH = float(max(0.0, np.mean(covs))) if covs else 0.0

    # ---- outer targets per policy ----
    # collect per (i,t): windowed mean, Z, and the true conditional (mean_log, sd_log) for D_{t+1}
    recs = []   # (i, wmean, kW1, qByAlphap dict, kBi_raw)
    for i in range(I):
        s2 = sig2 + (sd_eta ** 2 if unstable[i] else 0.0)
        sd_log = sqrt(s2)
        for t in outer_os:
            win = D[i, t - N:t]; m = win.mean()
            if m <= 0:
                continue
            Z = win / m
            e = bt.inner_eps(Z, ALPHA, EPSGRID)
            kW1 = bt.dro_k(Z, ALPHA, e)
            qap = {ap: bt.q_inv(Z, ap) for ap in ALPHAP}
            bi = inner_buffer(Z, ALPHA, BGRID)
            mean_log = mu[i] + (AR * X[i, t - 1] if unstable[i] else 0.0)  # cond mean of log D_t given info to t-1
            recs.append(dict(i=i, wmean=m, kW1=kW1, qap=qap, kBi=qap[ALPHA] + bi,
                             mean_log=mean_log, sd_log=sd_log, test=D[i, t] / m))
    if len(recs) < 20:
        return None
    kW1 = np.array([r['kW1'] for r in recs])
    L = kW1.mean()

    def vtrue(k_arr):
        v = np.empty(len(recs))
        for j, r in enumerate(recs):
            logS = log(max(1e-9, k_arr[j]) * r['wmean'])
            v[j] = 1.0 - Phi((logS - r['mean_log']) / r['sd_log'])
        return v

    def unit_R(k_arr):
        v = vtrue(k_arr)
        # per-unit mean v over its outer origins
        by = {}
        for j, r in enumerate(recs):
            by.setdefault(r['i'], []).append(v[j])
        gi = np.array([max(0.0, np.mean(vs) - ALPHA) for vs in by.values()])
        return cvar(gi), gi

    def ES(k_arr):
        t = np.array([r['test'] for r in recs])
        return float(np.mean(np.maximum(0.0, t - k_arr)))

    def inner_R_for_global(ap, b):
        # training-only reliability estimate via inner blocks (empirical undercoverage) for S=q_{1-ap}+b
        gi = []
        for i in range(I):
            vv = []
            for t in inner_os:
                win = D[i, t - N:t]; m = win.mean()
                if m <= 0:
                    continue
                Z = win / m
                vv.append(1.0 if D[i, t] / m > bt.q_inv(Z, ap) + b else 0.0)
            if vv:
                gi.append(max(0.0, np.mean(vv) - ALPHA))
        return cvar(gi) if gi else 1.0

    # W1
    R_W1, _ = unit_R(kW1); ES_W1 = ES(kW1)
    # reliability-optimized global buffer: for each alpha', exact-match b to mean inventory L, pick best inner R
    best = None
    for ap in ALPHAP:
        qA = np.array([r['qap'][ap] for r in recs])
        b = L - qA.mean()                     # exact global match to L
        if b < -0.5:
            continue
        Ri = inner_R_for_global(ap, b)
        if best is None or Ri < best[0]:
            best = (Ri, ap, b, qA + b)
    kGlob = best[3]
    R_glob, _ = unit_R(kGlob); ES_glob = ES(kGlob)
    # unit b_i matched to L by global shift
    kBi = np.array([r['kBi'] for r in recs]); kBi = kBi + (L - kBi.mean())
    R_bi, _ = unit_R(kBi); ES_bi = ES(kBi)
    # SAA and Fixed for reference
    kSAA = np.array([r['qap'][ALPHA] for r in recs])
    R_SAA, _ = unit_R(kSAA)
    kFix = np.full(len(recs), L); R_fix, _ = unit_R(kFix)

    return dict(PTH=PTH, L=float(L),
                R_W1=R_W1, R_glob=R_glob, R_bi=R_bi, R_SAA=R_SAA, R_fix=R_fix,
                ES_W1=ES_W1, ES_glob=ES_glob, ES_bi=ES_bi,
                dR_glob=R_W1 - R_glob, dR_bi=R_W1 - R_bi, dES_glob=ES_W1 - ES_glob,
                glob_ap=best[1])


def run_cell(r, N, M, seed):
    rng = np.random.default_rng(seed)
    T = N + K_INNER + K_OUTER
    rows = []
    for _ in range(M):
        D, X, mu, uns, sde = gen_panel(I_UNITS, T, r, rng)
        res = run_panel(D, X, mu, uns, sde, N)
        if res:
            rows.append(res)
    return rows


def m(rows, k): return float(np.mean([r[k] for r in rows]))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'validate'
    M = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    if mode == 'validate':
        for (r, N) in [(0.0, 48), (0.25, 48), (0.25, 96)]:
            rows = run_cell(r, N, M, seed=int(5000 + r * 1000 + N))
            print(f"r={r:<4} N={N:<3} M={len(rows):<3}: PTH={m(rows,'PTH'):+.5f}  "
                  f"dR-glob(W1-glob)={m(rows,'dR_glob'):+.5f}  dR-bi={m(rows,'dR_bi'):+.5f}  "
                  f"dES-glob={m(rows,'dES_glob'):+.5f}  "
                  f"(R: W1={m(rows,'R_W1'):.4f} glob={m(rows,'R_glob'):.4f} bi={m(rows,'R_bi'):.4f} "
                  f"SAA={m(rows,'R_SAA'):.4f} fix={m(rows,'R_fix'):.4f})", flush=True)
