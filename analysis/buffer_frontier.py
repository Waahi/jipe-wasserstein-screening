# -*- coding: utf-8 -*-
"""Decisive fixed-buffer experiment (STEP5F §7 FROZEN pre-registration, Codex thread 019f93b9).
PART 1: precompute cells by outer origin + per-policy service-inventory frontiers + attainable
ceilings + Wilks tolerance diagnostic. PART 2 (matched-L paired bootstrap) added after ceilings seen.

Cells reuse the frozen Gate-1/2/3 machinery: Z = windowed monthly burn / windowed-mean-burn,
days = k*30, shortfall = max(0, test-k), viol = test>k. Same 35 outer origins as Gate-2.
"""
import json, os, numpy as np
from collections import defaultdict
import backtest_v2 as bt   # saa, dro_k, inner_eps, wc_prob_exceed, q_inv

WIN = 48
MIN_OBS = 24
ALPHAS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]     # extended DOWN so quantile methods can be traced up
EPSGRID = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
SAA_REF_ALPHA = 0.05                                       # history-only reference for buffer + Gate-3 ΔR^req
CACHE = 'buffer_targets.json'                              # precomputed SAA/DRO k per cell per alpha (expensive DRO once)


def pctl(a, q):
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if len(a) else float('nan')


def build_cells():
    raw = json.load(open('coal_panel_2015_2024.json'))
    P = defaultdict(list)
    for kk, v in raw.items():
        p, y, m = kk.split('|')
        P[p].append((int(y), int(m), v['stock'], v['burn'], v['recv']))
    for p in P:
        P[p].sort()
    S = {}
    for p, seq in P.items():
        b = np.array([x[3] if x[3] else 0.0 for x in seq], float)
        if (b > 0).sum() < 36:
            continue
        S[p] = {(y, m): dict(stock=s, burn=bb, recv=r) for (y, m, s, bb, r) in seq}
    allmonths = sorted({ym for p in S for ym in S[p]})
    origins = list(range(WIN, len(allmonths) - 1))           # 35 outer origins
    cells_by_origin = []
    for oi, t0i in enumerate(origins):
        train_ms = allmonths[t0i - WIN + 1:t0i + 1]
        t_ym = allmonths[t0i]
        test_ym = allmonths[t0i + 1]
        cells = []
        for p, dd in S.items():
            wb = [dd[ym]['burn'] for ym in train_ms if ym in dd and dd[ym]['burn'] > 0]
            if len(wb) < MIN_OBS or t_ym not in dd or test_ym not in dd or dd[test_ym]['burn'] is None or dd[test_ym]['burn'] <= 0:
                continue
            mbm = float(np.mean(wb))
            if mbm <= 0:
                continue
            if dd[t_ym]['stock'] is None or dd[t_ym]['stock'] <= 0:
                continue
            twp = np.array([dd[ym]['burn'] for ym in train_ms if ym in dd and dd[ym]['burn'] > 0], float)
            Z = twp / mbm
            test_val = dd[test_ym]['burn'] / mbm
            I_t = float(dd[t_ym]['stock'])
            # gate3 history-only benchmarks (for the implementability axis)
            recv_hist = np.array([dd[ym]['recv'] for ym in train_ms
                                  if ym in dd and dd[ym]['recv'] is not None and dd[ym]['recv'] > 0], float)
            stock_hist = np.array([dd[ym]['stock'] for ym in train_ms
                                   if ym in dd and dd[ym]['stock'] is not None and dd[ym]['stock'] > 0], float)
            nb = []
            for ym in train_ms:
                if ym in dd:
                    nb.append((dd[ym]['recv'] or 0.0) - (dd[ym]['burn'] or 0.0))
            nb = np.array(nb, float); nb_pos = nb[nb > 0]
            if len(recv_hist) < 12 or len(stock_hist) < 12 or len(nb_pos) < 6:
                continue
            cells.append(dict(
                p=p, mbm=mbm, Z=Z, test=test_val, I_t=I_t,
                q_ref=float(np.quantile(Z, 1 - SAA_REF_ALPHA)),
                recv_p90=pctl(recv_hist, 90), recv_max=float(recv_hist.max()),
                stock_p90=pctl(stock_hist, 90), stock_max=float(stock_hist.max()),
                nb_p90=pctl(nb_pos, 90), nb_max=float(nb_pos.max()),
            ))
        cells_by_origin.append(cells)
    return cells_by_origin


def precompute_targets(cells_by_origin):
    """Expensive DRO/inner-eps computed ONCE per (cell, alpha); SAA quantile too. Slims out Z.
    Returns a JSON-serializable list-of-origins of slim cells with SAA/DRO target dicts."""
    out = []
    total = sum(len(c) for c in cells_by_origin)
    done = 0
    for cells in cells_by_origin:
        oc = []
        for c in cells:
            Z = c['Z']
            saa_t, dro_t = {}, {}
            for a in ALPHAS:
                saa_t[str(a)] = float(bt.q_inv(Z, a))
                eps = bt.inner_eps(Z, a, EPSGRID)
                dro_t[str(a)] = float(bt.dro_k(Z, a, eps))
            slim = {k: c[k] for k in ('p', 'mbm', 'test', 'I_t', 'q_ref',
                                      'recv_p90', 'recv_max', 'stock_p90', 'stock_max', 'nb_p90', 'nb_max')}
            slim['SAA'] = saa_t
            slim['DRO'] = dro_t
            oc.append(slim)
            done += 1
        out.append(oc)
        print(f"   precompute {done}/{total}", flush=True)
    return out


def load_or_build_targets():
    if os.path.exists(CACHE):
        print(f"loading cached targets {CACHE}")
        return json.load(open(CACHE))
    print("no cache -> building cells + precomputing targets (expensive DRO once)")
    cells_by_origin = build_cells()
    slim = precompute_targets(cells_by_origin)
    json.dump(slim, open(CACHE, 'w'))
    print(f"saved {CACHE}")
    return slim


def policy_target(cell, policy, param):
    """base-stock k (mean-burn units) from PRECOMPUTED slim cell."""
    if policy == 'SAA':
        return cell['SAA'][str(param)]
    if policy == 'DRO':
        return cell['DRO'][str(param)]
    if policy == 'FixedDays':
        return param / 30.0
    if policy == 'SAAbuf':
        return cell['q_ref'] + param
    raise ValueError(policy)


def pooled_inv_es_viol(cells_by_origin, policy, param):
    """origin-equal-weighted pooled mean inventory(days), expected shortfall, violation."""
    inv_o, es_o, vi_o = [], [], []
    for cells in cells_by_origin:
        ks, sh, vi = [], [], []
        for c in cells:
            k = policy_target(c, policy, param)
            ks.append(k * 30.0)
            sh.append(max(0.0, c['test'] - k))
            vi.append(1.0 if c['test'] > k else 0.0)
        if ks:
            inv_o.append(np.mean(ks)); es_o.append(np.mean(sh)); vi_o.append(np.mean(vi))
    return float(np.mean(inv_o)), float(np.mean(es_o)), float(np.mean(vi_o))


def main():
    cells_by_origin = load_or_build_targets()
    ncells = sum(len(c) for c in cells_by_origin)
    print(f"origins={len(cells_by_origin)}  cells(total plant-origins)={ncells}\n")

    # ---- per-policy frontier over param grid ----
    print("=== SERVICE-INVENTORY FRONTIERS (origin-equal-weighted) ===")
    grids = {
        'SAA': ALPHAS,
        'DRO': ALPHAS,
        'FixedDays': [45, 48, 51, 54, 57, 60, 63, 66],
        'SAAbuf': [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
    }
    frontiers = {}
    for pol, grid in grids.items():
        print(f"\n{pol}:")
        pts = []
        for prm in grid:
            inv, es, vi = pooled_inv_es_viol(cells_by_origin, pol, prm)
            pts.append((prm, inv, es, vi))
            print(f"   param={prm:<6} inv={inv:6.2f}d  ES={es:.4f}  viol={vi:.3f}")
        frontiers[pol] = pts

    # ---- attainable ceilings (max pooled inventory each method can honestly reach) ----
    print("\n=== ATTAINABLE POOLED-INVENTORY CEILINGS ===")
    for pol in ['SAA', 'DRO']:
        invs = [p[1] for p in frontiers[pol]]
        print(f"   {pol}: min={min(invs):.2f}d  max={max(invs):.2f}d  (at param={frontiers[pol][int(np.argmax(invs))][0]})")
    print("   FixedDays / SAAbuf: unbounded (can hit any L by construction)")

    # ---- Wilks nonparametric one-sided tolerance diagnostic (identification bound) ----
    print("\n=== WILKS TOLERANCE (what N=48 can identify) ===")
    N = WIN
    for a in [0.05, 0.02]:
        conf_max = 1 - (1 - a) ** N                       # confidence that sample max is a (1-a)-content upper bound
        n_needed = int(np.ceil(np.log(0.05) / np.log(1 - a)))
        print(f"   alpha={a}: sample-max as (1-alpha)-content one-sided bound -> confidence={conf_max*100:.1f}% ; "
              f"N for 95% confidence >= {n_needed}")

    # persist frontiers for PART 2
    json.dump({k: [[float(x) for x in pt] for pt in v] for k, v in frontiers.items()},
              open('buffer_frontiers.json', 'w'), indent=1)
    print("\nsaved buffer_frontiers.json")


if __name__ == '__main__':
    main()
