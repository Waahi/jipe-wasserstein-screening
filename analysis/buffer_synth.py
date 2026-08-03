# -*- coding: utf-8 -*-
"""Step 5h constructive regime (STEP5H FROZEN pre-reg, Codex 019f93ea). Controlled synthetic study:
when does service-form W1-DRO add value over a simple empirical buffer, and does a TRAINING-ONLY
diagnostic (TAI) predict the redundant->value boundary?

DGP: log D_it = mu_i + x_it + sigma z_it; x_it = 0.9 x_{i,t-1} + eta_it; half units stable (eta=0),
half unstable (eta~N(0,(r*sigma)^2)). Standardize by windowed mean. Axes r in {0,.10,.25} x N in {24,48,96}.
Comparators at matched mean inventory: W1-DRO(inner-eps), full global SAA+buffer (matched), unit b_i
(inner-calibrated), SAA, FixedDays. Panel = inference unit. TAI from inner origins only; ES from disjoint
later outer origins. Primary = beta_D in Delta_rc = b0 + beta_D*TAI + gamma_N.
"""
import sys, numpy as np
import backtest_v2 as bt

ALPHA = 0.05
EPSGRID = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75]
BGRID = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75]   # buffer grid (mean-burn units), same size as EPSGRID
I_UNITS = 80
K_INNER = 12
K_OUTER = 12
SIGMA = 0.35            # within-unit log sd (moderate right-skew lognormal)
AR = 0.9
R_LEVELS = [0.0, 0.10, 0.25]
N_LEVELS = [24, 48, 96]


def gen_panel(I, T, r, rng):
    D = np.empty((I, T))
    unstable = np.zeros(I, bool)
    unstable[I // 2:] = True                       # exactly 50/50
    mu = rng.normal(0.0, 0.3, I)                    # per-unit level (washes out under standardization)
    sd_eta = r * SIGMA
    for i in range(I):
        x = 0.0
        for t in range(T):
            if unstable[i] and sd_eta > 0:
                x = AR * x + rng.normal(0.0, sd_eta)
            D[i, t] = np.exp(mu[i] + x + rng.normal(0.0, SIGMA))
    return D


def inner_buffer(Z, alpha, bgrid):
    """smallest additive buffer b (on empirical quantile) whose inner leave-last-h-out OOS viol <= alpha."""
    n = len(Z)
    if n < 16:
        return 0.0
    for b in bgrid:
        viol = []
        for h in range(min(8, n // 4), 0, -1):
            fit = Z[:-h]; test = Z[-h]
            if len(fit) < 8:
                continue
            k = bt.q_inv(fit, alpha) + b
            viol.append(1.0 if test > k else 0.0)
        if viol and np.mean(viol) <= alpha:
            return b
    return bgrid[-1]


def run_panel(D, N, rng):
    """returns dict of ES per policy at matched inventory + TAI + eps dispersion, or None."""
    I, T = D.shape
    inner_os = range(N, N + K_INNER)
    outer_os = range(N + K_INNER, N + K_INNER + K_OUTER)
    # --- TAI from inner origins (SAA undercoverage per unit) ---
    ptilde = []
    for i in range(I):
        v = []
        for t in inner_os:
            win = D[i, t - N:t]; m = win.mean()
            if m <= 0:
                continue
            Z = win / m; test = D[i, t] / m
            v.append(1.0 if test > bt.q_inv(Z, ALPHA) else 0.0)
        if v:
            ptilde.append(np.mean(v))
    ptilde = np.array(ptilde)
    if len(ptilde) < 4:
        return None
    varhat = np.mean(ptilde * (1 - ptilde) / K_INNER)
    TAI = float(np.sqrt(max(0.0, np.var(ptilde - ALPHA) - varhat)))
    # --- outer origins: policy targets + ES ---
    kW1, kSAA, kBi, test_all, eps_all = [], [], [], [], []
    for i in range(I):
        for t in outer_os:
            win = D[i, t - N:t]; m = win.mean()
            if m <= 0:
                continue
            Z = win / m; test = D[i, t] / m
            e = bt.inner_eps(Z, ALPHA, EPSGRID)
            kW1.append(bt.dro_k(Z, ALPHA, e)); eps_all.append(e)
            q = bt.q_inv(Z, ALPHA); kSAA.append(q)
            kBi.append(q + inner_buffer(Z, ALPHA, BGRID))
            test_all.append(test)
    kW1 = np.array(kW1); kSAA = np.array(kSAA); kBi = np.array(kBi); test_all = np.array(test_all)
    eps_all = np.array(eps_all)
    if len(kW1) < 20:
        return None
    L = kW1.mean()                                   # matched inventory (mean-burn units)
    bstar = L - kSAA.mean()                           # global additive buffer matched exactly to L
    kGlob = kSAA + bstar
    # match unit-b_i policy to same mean L by a global shift too (fair: same resource)
    kBi_m = kBi + (L - kBi.mean())
    kFix = np.full_like(test_all, L)
    def ES(k): return float(np.mean(np.maximum(0.0, test_all - k)))
    return dict(TAI=TAI, L=float(L), eps_share=float((eps_all > 0).mean()), eps_sd=float(np.std(eps_all)),
                ES_W1=ES(kW1), ES_glob=ES(kGlob), ES_bi=ES(kBi_m), ES_SAA=ES(kSAA), ES_fix=ES(kFix),
                bstar=float(bstar))


def run_cell(r, N, M, seed):
    rng = np.random.default_rng(seed)
    T = N + K_INNER + K_OUTER
    rows = []
    for _ in range(M):
        D = gen_panel(I_UNITS, T, r, rng)
        res = run_panel(D, N, rng)
        if res:
            res['dW1_glob'] = res['ES_W1'] - res['ES_glob']
            res['dW1_bi'] = res['ES_W1'] - res['ES_bi']
            res['dW1_fix'] = res['ES_W1'] - res['ES_fix']
            rows.append(res)
    return rows


def summarize(rows):
    import numpy as np
    a = lambda k: np.array([r[k] for r in rows])
    return dict(n=len(rows), TAI=float(a('TAI').mean()), L=float(a('L').mean()),
                dW1_glob=float(a('dW1_glob').mean()), dW1_bi=float(a('dW1_bi').mean()),
                dW1_fix=float(a('dW1_fix').mean()), eps_share=float(a('eps_share').mean()),
                eps_sd=float(a('eps_sd').mean()),
                ES_W1=float(a('ES_W1').mean()), ES_glob=float(a('ES_glob').mean()), ES_bi=float(a('ES_bi').mean()))


def summ2(rows):
    a = lambda k: np.array([r[k] for r in rows])
    return dict(n=len(rows), TAI=float(a('TAI').mean()),
                dW1_glob=float(a('dW1_glob').mean()),
                dbi_glob=float((a('ES_bi') - a('ES_glob')).mean()),
                dW1_bi=float(a('dW1_bi').mean()),
                ES_W1=float(a('ES_W1').mean()), ES_glob=float(a('ES_glob').mean()), ES_bi=float(a('ES_bi').mean()),
                eps_share=float(a('eps_share').mean()), eps_sd=float(a('eps_sd').mean()))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'sanity'
    M = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    if mode == 'diag':
        # locate whether ANY per-unit adaptation beats global buffer, across identifiability
        for (r, N) in [(0.0, 96), (0.10, 96), (0.25, 96), (0.25, 48), (0.25, 24)]:
            rows = run_cell(r, N, M, seed=int(1000 + r * 1000 + N))
            s = summ2(rows)
            print(f"r={r:<4} N={N:<3} M={s['n']:<3}: TAI={s['TAI']:.4f}  "
                  f"dW1-glob={s['dW1_glob']:+.4f}  dbi-glob={s['dbi_glob']:+.4f}  dW1-bi={s['dW1_bi']:+.4f}  "
                  f"eps_share={s['eps_share']:.2f} eps_sd={s['eps_sd']:.3f}  "
                  f"(ES W1={s['ES_W1']:.4f} glob={s['ES_glob']:.4f} bi={s['ES_bi']:.4f})", flush=True)
    elif mode == 'sanity':
        for r in [0.0, 0.25]:
            rows = run_cell(r, 48, M, seed=100 + int(r * 100))
            s = summarize(rows)
            print(f"r={r} N=48 M={s['n']}: TAI={s['TAI']:.4f}  L={s['L']:.2f}  "
                  f"dW1-glob={s['dW1_glob']:+.4f}  dW1-bi={s['dW1_bi']:+.4f}  dW1-fix={s['dW1_fix']:+.4f}  "
                  f"eps_share={s['eps_share']:.2f} eps_sd={s['eps_sd']:.3f}", flush=True)
