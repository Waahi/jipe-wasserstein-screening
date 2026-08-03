# -*- coding: utf-8 -*-
"""Step 5h CONFIRMATORY large-M recompute of the frozen 3×3 (STEP5H §9). Codex-signed inference
(thread 019f9513): within-cell PAIRED panel bootstrap; CENTERED max-t simultaneous bands; G1 = equal-
weight average of the three r=0.25 N-cells (in the max-t family); keep N fixed effects for beta_P and
also report beta_P*(PTH range). Produces publishable bands + 4-gate PASS/FAIL. Expected: all gates FAIL
(W1 worse than the fair buffers even at r=0) -> confirms the redundancy-diagnostic paper.
"""
import json, numpy as np
import buffer_reliability as br

# frozen grid + shrunk panel geometry for tractable large-M confirmatory run
br.I_UNITS = 60
br.K_OUTER = 10
R_LEVELS = [0.0, 0.10, 0.25]
N_LEVELS = [24, 48, 96]
M_PER_CELL = 80
B = 6000
DELTA = 0.005
SEED = 20250724


def gen_cell(r, N, M, seed):
    rng = np.random.default_rng(seed)
    T = N + br.K_INNER + br.K_OUTER
    rows = []
    for _ in range(M):
        D, X, mu, uns, sde = br.gen_panel(br.I_UNITS, T, r, rng)
        res = br.run_panel(D, X, mu, uns, sde, N)
        if res:
            rows.append((res['R_W1'] - res['R_glob'],      # dR
                         res['ES_W1'] - res['ES_glob'],     # dES
                         res['R_W1'] - res['R_bi'],         # dbi
                         res['PTH']))
    return np.array(rows)   # [m,4] columns dR,dES,dbi,PTH


_NDUM = np.array([[1.0 if N == 48 else 0.0, 1.0 if N == 96 else 0.0]
                  for r in R_LEVELS for N in N_LEVELS])   # N=48,N=96 dummies (N=24 baseline)


def ols_betaP(dR_cells, PTH_cells):
    # design: intercept, PTH, N=48 dummy, N=96 dummy
    X = np.column_stack([np.ones(len(dR_cells)), np.asarray(PTH_cells, float), _NDUM])
    beta, *_ = np.linalg.lstsq(X, np.asarray(dR_cells, float), rcond=None)
    return beta[1]   # PTH coefficient


def main():
    import os
    cells = [(r, N) for r in R_LEVELS for N in N_LEVELS]
    CACHE = 'confirm_panels.npz'
    panels = {}
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        for k, c in enumerate(cells):
            panels[c] = z[f'c{k}']
        print(f"loaded cached panels {CACHE}", flush=True)
    else:
        for k, (r, N) in enumerate(cells):
            panels[(r, N)] = gen_cell(r, N, M_PER_CELL, SEED + 1000 * k)
            print(f"  gen r={r} N={N}: {len(panels[(r,N)])} panels", flush=True)
        np.savez(CACHE, **{f'c{k}': panels[c] for k, c in enumerate(cells)})
        print(f"saved {CACHE}", flush=True)
    # cell point estimates
    dR = np.array([panels[c][:, 0].mean() for c in cells])
    dES = np.array([panels[c][:, 1].mean() for c in cells])
    dbi = np.array([panels[c][:, 2].mean() for c in cells])
    PTH = np.array([panels[c][:, 3].mean() for c in cells])
    idx_r25 = [i for i, c in enumerate(cells) if c[0] == 0.25]
    idx_r0 = [i for i, c in enumerate(cells) if c[0] == 0.0]
    G1_point = dR[idx_r25].mean()
    betaP_point = ols_betaP(dR, PTH)

    rng = np.random.default_rng(SEED + 99)
    Bdr = np.zeros((B, len(cells))); BdES = np.zeros((B, len(cells))); Bdbi = np.zeros((B, len(cells)))
    BG1 = np.zeros(B); BbP = np.zeros(B)
    for b in range(B):
        dR_b = np.empty(len(cells)); dES_b = np.empty(len(cells)); dbi_b = np.empty(len(cells)); PTH_b = np.empty(len(cells))
        for i, c in enumerate(cells):
            P = panels[c]; m = len(P)
            take = rng.integers(0, m, m)             # paired resample of whole panel rows
            S = P[take]
            dR_b[i] = S[:, 0].mean(); dES_b[i] = S[:, 1].mean(); dbi_b[i] = S[:, 2].mean(); PTH_b[i] = S[:, 3].mean()
        Bdr[b] = dR_b; BdES[b] = dES_b; Bdbi[b] = dbi_b
        BG1[b] = dR_b[idx_r25].mean()
        BbP[b] = ols_betaP(dR_b, PTH_b)

    def band(point_vec, boot_mat):
        sd = boot_mat.std(axis=0, ddof=1)
        return sd
    sd_dR = Bdr.std(0, ddof=1); sd_dES = BdES.std(0, ddof=1); sd_dbi = Bdbi.std(0, ddof=1); sd_G1 = BG1.std(ddof=1)
    # centered max-t over the family {dR(9), dES(9), dbi(9), G1}
    fam_pt = np.concatenate([dR, dES, dbi, [G1_point]])
    fam_boot = np.column_stack([Bdr, BdES, Bdbi, BG1[:, None]])
    fam_sd = fam_boot.std(0, ddof=1)
    tstats = np.abs(fam_boot - fam_pt) / np.where(fam_sd > 0, fam_sd, 1e9)
    crit = float(np.quantile(tstats.max(axis=1), 0.95))
    print(f"\nmax-t simultaneous crit (95%, family size {len(fam_pt)}) = {crit:.2f}\n")

    def simband(pt, sd): return (pt - crit * sd, pt + crit * sd)

    print("=== per-cell Δ_R = R_W1 − R_BestGlobal (positive = W1 worse on worst-case reliability) ===")
    for i, c in enumerate(cells):
        lo, hi = simband(dR[i], sd_dR[i])
        print(f"  r={c[0]:<4} N={c[1]:<3}: Δ_R={dR[i]:+.4f} sim95=[{lo:+.4f},{hi:+.4f}]  PTH={PTH[i]:+.5f}")
    lo, hi = simband(G1_point, sd_G1)
    print(f"\nG1 pooled Δ_R(r=0.25, equal-wt over N) = {G1_point:+.4f} sim95=[{lo:+.4f},{hi:+.4f}]  "
          f"-> {'PASS(<-0.005)' if hi < -DELTA else 'FAIL'}")

    # G2: r=0 cells equivalence
    print("\nG2 (r=0 negative control, expected equivalence ⊂±0.005):")
    g2ok = True
    for i in idx_r0:
        lo, hi = simband(dR[i], sd_dR[i])
        ok = (lo >= -DELTA and hi <= DELTA)
        g2ok &= ok
        print(f"  r=0 N={cells[i][1]:<3}: Δ_R={dR[i]:+.4f} sim95=[{lo:+.4f},{hi:+.4f}] {'⊂±.005' if ok else 'OUTSIDE'}")
    # G3 mean-ES guardrail: pooled dES over r=0.25
    G3_point = dES[idx_r25].mean(); G3_sd = BdES[:, idx_r25].mean(1).std(ddof=1)
    lo3, hi3 = (G3_point - crit * G3_sd, G3_point + crit * G3_sd)
    # G4 W1 vs b_i pooled over r=0.25
    G4_point = dbi[idx_r25].mean(); G4_sd = Bdbi[:, idx_r25].mean(1).std(ddof=1)
    lo4, hi4 = (G4_point - crit * G4_sd, G4_point + crit * G4_sd)
    # beta_P
    bP_sd = BbP.std(ddof=1); bP_hi = betaP_point + 1.645 * bP_sd   # one-sided 95% upper
    PTH_range = PTH.max() - PTH.min()

    print(f"\nG3 mean-ES guardrail Δ_ES(r=.25)={G3_point:+.4f} sim95=[{lo3:+.4f},{hi3:+.4f}] "
          f"-> {'PASS(<+0.005)' if hi3 < DELTA else 'FAIL(W1 harms mean-ES)'}")
    print(f"G4 W1 vs b_i Δ_bi(r=.25)={G4_point:+.4f} sim95=[{lo4:+.4f},{hi4:+.4f}] "
          f"-> {'PASS(<+0.005)' if hi4 < DELTA else 'FAIL'}")
    print(f"beta_P={betaP_point:+.4f} one-sided95upper={bP_hi:+.4f} (want<0) ; PTH range={PTH_range:.5f} ; "
          f"beta_P*range={betaP_point*PTH_range:+.5f}")

    G1pass = hi < -DELTA
    verdict = "CONSTRUCTIVE ELEMENT FAILS -> redundancy-diagnostic paper confirmed" if not G1pass else "PASS?"
    print(f"\n=== VERDICT: {verdict} ===")
    out = dict(cells=[list(c) for c in cells], crit=crit,
               dR=dR.tolist(), sd_dR=sd_dR.tolist(), PTH=PTH.tolist(),
               dES=dES.tolist(), dbi=dbi.tolist(),
               G1=dict(point=G1_point, sim=[float(x) for x in simband(G1_point, sd_G1)]),
               G2_r0=[dict(N=cells[i][1], point=float(dR[i]), sim=[float(x) for x in simband(dR[i], sd_dR[i])]) for i in idx_r0],
               G3=dict(point=G3_point, sim=[lo3, hi3]), G4=dict(point=G4_point, sim=[lo4, hi4]),
               betaP=betaP_point, betaP_upper=bP_hi, PTH_range=PTH_range,
               M_per_cell=M_PER_CELL, B=B, I_units=br.I_UNITS, K_outer=br.K_OUTER)
    json.dump(out, open('buffer_confirm_report.json', 'w'), indent=1)
    print("saved buffer_confirm_report.json")


if __name__ == '__main__':
    main()
