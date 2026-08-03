# -*- coding: utf-8 -*-
"""Decisive fixed-buffer experiment PART 2 (STEP5F §7 FROZEN pre-reg, Codex 019f93b9).
Vectorized: per-origin numpy arrays cached once; shared block-bootstrap draws across all
comparisons/regimes; global-lambda matching re-solved inside each replicate.

7 locked decisions honored: additive SAA+buffer; ONE global param per (policy,L) via global-lambda
interpolation between two bracketing frontier points (no per-origin matching); inference unit = 35
outer origins, circular block bootstrap L_block=4, re-match inside each replicate; origin-equal-weighted
matching (= ES estimand weighting); SAA only on attainable support; two axes no weighting; three-state
verdict vs delta_ES=0.005.
"""
import json, numpy as np

ALPHAS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
FIXED_D = [45, 48, 51, 54, 57, 60, 63, 66]
SAABUF_B = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
L_GRID = [52, 54, 55, 56, 57, 58, 60, 63]
DELTA_ES = 0.005
B = 1000
L_BLOCK = 4
SEED = 20250724


def load():
    raw = json.load(open('buffer_targets.json'))
    O = []
    for cells in raw:
        if not cells:
            continue
        d = dict(
            test=np.array([c['test'] for c in cells], float),
            mbm=np.array([c['mbm'] for c in cells], float),
            I_t=np.array([c['I_t'] for c in cells], float),
            q_ref=np.array([c['q_ref'] for c in cells], float),
            recv_p90=np.array([c['recv_p90'] for c in cells], float),
            recv_max=np.array([c['recv_max'] for c in cells], float),
            stock_p90=np.array([c['stock_p90'] for c in cells], float),
            stock_max=np.array([c['stock_max'] for c in cells], float),
            nb_p90=np.array([c['nb_p90'] for c in cells], float),
            nb_max=np.array([c['nb_max'] for c in cells], float),
            SAA={a: np.array([c['SAA'][str(a)] for c in cells], float) for a in ALPHAS},
            DRO={a: np.array([c['DRO'][str(a)] for c in cells], float) for a in ALPHAS},
        )
        O.append(d)
    return O


def karr(o, policy, param):
    if policy == 'SAA':
        return o['SAA'][param]
    if policy == 'DRO':
        return o['DRO'][param]
    if policy == 'FixedDays':
        return np.full_like(o['mbm'], param / 30.0)
    if policy == 'SAAbuf':
        return o['q_ref'] + param
    raise ValueError


def pooled_inv(O, policy, param):
    return float(np.mean([np.mean(karr(o, policy, param)) * 30.0 for o in O]))


def frontier(O, policy):
    grid = {'SAA': ALPHAS, 'DRO': ALPHAS, 'FixedDays': FIXED_D, 'SAAbuf': SAABUF_B}[policy]
    return [(prm, pooled_inv(O, policy, prm)) for prm in grid]


def bracket(front, L):
    fs = sorted(front, key=lambda x: x[1])
    invs = [f[1] for f in fs]
    if L < invs[0] - 1e-9 or L > invs[-1] + 1e-9:
        return None
    for i in range(len(fs) - 1):
        if fs[i][1] - 1e-9 <= L <= fs[i + 1][1] + 1e-9:
            return (fs[i + 1][0], fs[i][0])   # (p_hi=higher inv, p_lo=lower inv)
    return (fs[-1][0], fs[-2][0])


def short_per_origin(O, idxs, policy, p_hi, p_lo, L, regime):
    """global-lambda match on origin subset idxs to pooled mean=L; per-origin mean shortfall array."""
    khi_o, klo_o, test_o, mask_o = [], [], [], []
    ih, il = [], []
    for oi in idxs:
        o = O[oi]
        khi = karr(o, policy, p_hi); klo = karr(o, policy, p_lo); test = o['test']
        if regime is not None:
            build = (L / 30.0) * o['mbm'] > o['I_t']
            m = build if regime == 'build' else ~build
            if not m.any():
                khi_o.append(None); continue
            khi, klo, test = khi[m], klo[m], test[m]
        khi_o.append(khi); klo_o.append(klo); test_o.append(test)
        ih.append(np.mean(khi) * 30.0); il.append(np.mean(klo) * 30.0)
    if not ih:
        return None
    IH, IL = np.mean(ih), np.mean(il)
    lam = 0.5 if abs(IH - IL) < 1e-12 else min(1.0, max(0.0, (L - IL) / (IH - IL)))
    s = []
    ti = 0
    for khi in khi_o:
        if khi is None:
            continue
        klo = klo_o[ti]; test = test_o[ti]; ti += 1
        k = lam * khi + (1 - lam) * klo
        s.append(np.mean(np.maximum(0.0, test - k)))
    return np.array(s) if s else None


def paired_band(O, polA, polB, frontA, frontB, boot_idx, regime):
    n = len(O)
    allidx = list(range(n))
    brA = {L: bracket(frontA, L) for L in L_GRID}
    brB = {L: bracket(frontB, L) for L in L_GRID}
    Ls = [L for L in L_GRID if brA[L] and brB[L]]
    point = {}
    for L in Ls:
        sA = short_per_origin(O, allidx, polA, *brA[L], L, regime)
        sB = short_per_origin(O, allidx, polB, *brB[L], L, regime)
        point[L] = None if (sA is None or sB is None or len(sA) != len(sB)) else float(np.mean(sA - sB))
    Ls = [L for L in Ls if point[L] is not None]
    if not Ls:
        return None
    boot = {L: np.full(len(boot_idx), np.nan) for L in Ls}
    for bi, idx in enumerate(boot_idx):
        for L in Ls:
            sA = short_per_origin(O, idx, polA, *brA[L], L, regime)
            sB = short_per_origin(O, idx, polB, *brB[L], L, regime)
            if sA is not None and sB is not None and len(sA) == len(sB):
                boot[L][bi] = np.mean(sA - sB)
    sd = {L: float(np.nanstd(boot[L], ddof=1)) for L in Ls}
    tmax = []
    for bi in range(len(boot_idx)):
        ts = [abs(boot[L][bi] - point[L]) / sd[L] for L in Ls if sd[L] > 0 and not np.isnan(boot[L][bi])]
        if ts:
            tmax.append(max(ts))
    crit = float(np.quantile(tmax, 0.95)) if tmax else float('nan')
    sim = {L: (point[L] - crit * sd[L], point[L] + crit * sd[L]) for L in Ls}
    marg = {L: (float(np.nanpercentile(boot[L], 2.5)), float(np.nanpercentile(boot[L], 97.5))) for L in Ls}
    return dict(Ls=Ls, point=point, sd=sd, crit=crit, sim=sim, marg=marg)


def classify(x, p90, mx):
    return 'Routine' if x <= p90 else ('Exceptional' if x <= mx else 'Unsupported')


def implementability(O, policy, front, L):
    br = bracket(front, L)
    if br is None:
        return None
    p_hi, p_lo = br
    IH = pooled_inv(O, policy, p_hi); IL = pooled_inv(O, policy, p_lo)
    lam = 0.5 if abs(IH - IL) < 1e-12 else min(1.0, max(0.0, (L - IL) / (IH - IL)))
    nc = npbn = npbnu = nbu = 0
    for o in O:
        k = lam * karr(o, policy, p_hi) + (1 - lam) * karr(o, policy, p_lo)
        mbm = o['mbm']; I_t = o['I_t']; tt = k * mbm
        R_req = np.maximum(0.0, tt + mbm - I_t)
        R_saa = np.maximum(0.0, o['q_ref'] * mbm + mbm - I_t)
        new_action = R_req > R_saa + 1e-6 * mbm
        build_pos = tt > I_t
        need = np.maximum(0.0, tt - I_t)
        for i in range(len(k)):
            cs = 'Routine' if I_t[i] >= tt[i] else classify(tt[i], o['stock_p90'][i], o['stock_max'][i])
            cn = classify(need[i], o['nb_p90'][i], o['nb_max'][i]) if build_pos[i] else None
            cr = classify(R_req[i], o['recv_p90'][i], o['recv_max'][i])
            order = {'Routine': 0, 'Exceptional': 1, 'Unsupported': 2}
            applic = [cs, cr] + ([cn] if cn else [])
            binding = max(applic, key=lambda c: order[c])
            nc += 1
            if new_action[i] and build_pos[i]:
                npbn += 1
                if binding == 'Unsupported':
                    npbnu += 1; nbu += 1
    return dict(L=L, U_p=nbu / nc, n_pilebuild_new=npbn,
                cond_unsup=(npbnu / npbn if npbn else float('nan')), lam=lam)


def main():
    O = load()
    n = len(O)
    print(f"origins={n}  cells={sum(len(o['test']) for o in O)}\n")
    fronts = {pol: frontier(O, pol) for pol in ['SAA', 'DRO', 'FixedDays', 'SAAbuf']}
    print("=== attainable pooled-inv ranges ===")
    for pol in fronts:
        invs = [f[1] for f in fronts[pol]]
        print(f"   {pol}: [{min(invs):.2f}, {max(invs):.2f}] d")

    rng = np.random.default_rng(SEED)
    boot_idx = []
    for _ in range(B):
        idx = []
        while len(idx) < n:
            s = int(rng.integers(0, n))
            idx.extend([(s + j) % n for j in range(L_BLOCK)])
        boot_idx.append(idx[:n])

    report = {'primary_ES': {}, 'implementability': {}, 'frontiers': {k: fronts[k] for k in fronts}}
    for (A, Bp) in [('DRO', 'FixedDays'), ('DRO', 'SAAbuf'), ('SAA', 'FixedDays')]:
        print(f"\n########## {A} - {Bp}  (positive = {A} worse) ##########")
        report['primary_ES'][f'{A}-{Bp}'] = {}
        for regime in ['pooled', 'maint', 'build']:
            reg = None if regime == 'pooled' else regime
            res = paired_band(O, A, Bp, fronts[A], fronts[Bp], boot_idx, reg)
            if res is None:
                print(f"  [{regime}] no common attainable L"); continue
            print(f"  [{regime}] L={res['Ls']}  max-t crit={res['crit']:.2f}")
            rr = {}
            for L in res['Ls']:
                lo, hi = res['sim'][L]; mlo, mhi = res['marg'][L]
                flag = 'ADV' if hi < -DELTA_ES else ('EQUIV' if (lo >= -DELTA_ES and hi <= DELTA_ES) else 'incon')
                print(f"     L={L}: Δ={res['point'][L]:+.4f} sim95=[{lo:+.4f},{hi:+.4f}] marg95=[{mlo:+.4f},{mhi:+.4f}] {flag}")
                rr[str(L)] = dict(point=res['point'][L], sim=[lo, hi], marg=[mlo, mhi], flag=flag)
            report['primary_ES'][f'{A}-{Bp}'][regime] = dict(crit=res['crit'], perL=rr)

    print("\n########## IMPLEMENTABILITY (U_p at matched inventory, Gate-3 tie-in) ##########")
    for pol in ['SAA', 'DRO', 'FixedDays', 'SAAbuf']:
        report['implementability'][pol] = {}
        for L in [56, 58, 60, 63]:
            r = implementability(O, pol, fronts[pol], L)
            if r is None:
                print(f"   {pol} L={L}: not attainable"); continue
            print(f"   {pol} L={L}: U_p={r['U_p']*100:.1f}%  pileB-new={r['n_pilebuild_new']}  cond-unsup={r['cond_unsup']*100:.1f}%  lam={r['lam']:.2f}")
            report['implementability'][pol][str(L)] = r

    json.dump(report, open('buffer_bootstrap_report.json', 'w'), indent=1)
    print("\nsaved buffer_bootstrap_report.json")


if __name__ == '__main__':
    main()
