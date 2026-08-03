# -*- coding: utf-8 -*-
"""Step 5 backtest — ONE outer fold end-to-end, with an explicit information-timestamp audit.
Codex D: run one fold and reconcile timestamps BEFORE the full run.

Design (frozen):
  demand Z = standardized monthly coal burn (1.0 = plant mean; days = k*30), H=1 protection period.
  At each outer origin t0 (month-end): TRAIN window = the W months ending at t0 (inclusive).
    - fit each method's base-stock k using ONLY data dated <= t0
    - DRO epsilon chosen INNER-only (rolling pseudo-origins strictly inside the train window)
  EVALUATE on the realized next month burn Z_{t0+1} (strictly AFTER t0): violation = Z_{t0+1} > k.
  Report per method: base-stock k (days), realized violation, shortfall depth, implied inventory.

Leakage audit prints, for the fold, the exact month ranges used for train / inner-calib / test so a
human can verify test month > all training months for every plant.
"""
import json, numpy as np
from collections import defaultdict

# ---- corrected operator (fractional transport; == transport LP) ----
def wc_prob_exceed(Z, k, eps):
    S=len(Z); base=np.mean(Z>k)
    below=np.sort(k-Z[Z<=k]); budget=eps; extra=0.0
    for gap in below:
        cost=gap/S
        if cost<=budget: budget-=cost; extra+=1.0/S
        else:
            if gap>0: extra+=(budget/(gap/S))*(1.0/S)
            budget=0.0; break
    return base+extra

def saa_service(Z, alpha):                      # ε=0 baseline (SAA == non-robust rolling quantile)
    return float(np.quantile(Z, 1-alpha, method='inverted_cdf'))

def dro_chance(Z, alpha, eps):
    lo=0.0; hi=max(0.0,np.max(Z))+1.0
    if wc_prob_exceed(Z,lo,eps)<=alpha: return 0.0
    for _ in range(80):
        mid=0.5*(lo+hi)
        if wc_prob_exceed(Z,mid,eps)<=alpha: hi=mid
        else: lo=mid
    return hi

def fixed_dob(Z, days=30.0):                     # naive fixed days-of-burn rule (k in mean-burn units)
    return days/30.0

def vanderlaan_ks(Z, alpha):
    """van der Laan-style KS/W_inf service-level: inflate the empirical quantile by the DKW band.
    k = quantile(Z, 1-alpha+ dkw) where dkw = sqrt(ln(2/delta)/(2n)); delta=alpha (one config)."""
    n=len(Z); dkw=np.sqrt(np.log(2/alpha)/(2*n))
    lvl=min(0.999, 1-alpha+dkw)
    return float(np.quantile(Z, lvl, method='inverted_cdf'))

# ---- inner-only epsilon selection: smallest eps whose inner-OOS violation <= alpha ----
def select_eps_inner(train_series, alpha, eps_grid):
    """train_series: list of standardized-burn arrays already restricted to the train window.
    Inner rolling-origin: for each plant, hold out its last few train months as inner-test."""
    best=0.0
    for eps in eps_grid:
        viol=[]
        for Z in train_series:
            if len(Z)<12: continue
            n_inner=min(6, len(Z)//4)
            for h in range(n_inner,0,-1):
                fitZ=Z[:-h]; test=Z[-h]
                if len(fitZ)<8: continue
                k=dro_chance(fitZ[fitZ>0], alpha, eps)
                viol.append(1.0 if test>k else 0.0)
        if viol and np.mean(viol)<=alpha:
            best=eps; break            # smallest eps achieving inner alpha (grid ascending)
    return best

def main():
    raw=json.load(open('coal_panel_2015_2024.json'))
    P=defaultdict(list)
    for kk,v in raw.items():
        p,y,m=kk.split('|'); P[p].append((int(y),int(m),v['stock'],v['burn'],v['recv']))
    for p in P: P[p].sort()
    # RAW burn series with (y,m) index — standardization is done PER-FOLD with train-window mean only
    # (fixes the look-ahead: the test month must NOT enter the normalizing mean).
    S={}
    for p,seq in P.items():
        b=np.array([x[3] if x[3] else 0.0 for x in seq],float); pos=b[b>0]
        if len(pos)<36: continue
        S[p]=[(y,m,bb) for (y,m,s,bb,r) in seq]     # RAW tons, not standardized

    ALPHA=0.05; WIN=48; EPS_GRID=[0.0,0.02,0.05,0.10,0.15,0.20,0.30]
    # pick ONE outer origin: use month index so that a 48-month train window exists and a test month follows.
    # Build a global month axis.
    allmonths=sorted({(y,m) for p in S for (y,m,z) in S[p]})
    mi={ym:i for i,ym in enumerate(allmonths)}
    # choose origin at 60 months in (leaves >=48 train and a test month)
    t0_idx=60
    t0=allmonths[t0_idx]; test_ym=allmonths[t0_idx+1]
    train_lo=allmonths[t0_idx-WIN+1]
    print(f"=== ONE OUTER FOLD | origin t0={t0}  test={test_ym}  train=[{train_lo} .. {t0}] ({WIN} mo) ===\n")

    # assemble per-plant train arrays (months in [train_lo, t0]) and the test value (month test_ym)
    train_series=[]; eval_rows=[]
    for p,seq in S.items():
        dd={(y,m):z for (y,m,z) in seq}
        tw_raw=np.array([dd[ym] for ym in allmonths[t0_idx-WIN+1:t0_idx+1] if ym in dd],float)
        twp_raw=tw_raw[tw_raw>0]
        if len(twp_raw)<24: continue
        if test_ym not in dd: continue
        test_raw=dd[test_ym]
        if test_raw<=0: continue           # idle test month -> undefined coverage, skip (Step-2 rule)
        mb_train=twp_raw.mean()            # train-window mean ONLY (no test leakage)
        if mb_train<=0: continue
        twp=twp_raw/mb_train               # standardized demand, train-window normalization
        test_val=test_raw/mb_train         # test standardized by the SAME train-only mean
        train_series.append(twp)
        eval_rows.append((p, twp, test_val))
    print(f"plants in this fold (>=24 positive train months + positive test burn): {len(eval_rows)}")

    # timestamp/leakage audit
    print("\nLEAKAGE AUDIT (fold-level):")
    print(f"  train months : {allmonths[t0_idx-WIN+1]} .. {allmonths[t0_idx]}  (all <= origin)")
    print(f"  test month   : {test_ym}  (strictly after origin: {test_ym>t0})")
    print(f"  inner-calib  : pseudo-origins strictly inside train window (last<=6 months per plant)")

    # inner-only epsilon
    eps_star=select_eps_inner(train_series, ALPHA, EPS_GRID)
    print(f"\ninner-selected epsilon* = {eps_star}")

    # evaluate each method on this fold
    methods={}
    for name in ['SAA(eps0)','DRO(eps*)','fixed30d','forecastQ','vanderLaan']:
        ks=[]; viol=[]; short=[]
        for (p,twp,test_val) in eval_rows:
            if name=='SAA(eps0)': k=saa_service(twp,ALPHA)
            elif name=='DRO(eps*)': k=dro_chance(twp,ALPHA,eps_star)
            elif name=='fixed30d': k=fixed_dob(twp,30.0)
            elif name=='forecastQ': k=saa_service(twp,ALPHA)  # forecast-then-quantile ~ SAA on stationary std burn (placeholder = SAA)
            elif name=='vanderLaan': k=vanderlaan_ks(twp,ALPHA)
            ks.append(k); viol.append(1.0 if test_val>k else 0.0)
            short.append(max(0.0, test_val-k))
        methods[name]=dict(k_days=np.mean(ks)*30, viol=np.mean(viol),
                           short_mean=np.mean(short), inv=np.mean(ks))
    print(f"\n{'method':12s} {'k(days)':>8s} {'viol':>7s} {'target':>7s} {'shortfall':>10s} {'inv(k)':>7s}")
    for name,r in methods.items():
        print(f"{name:12s} {r['k_days']:8.1f} {r['viol']:7.3f} {ALPHA:7.2f} {r['short_mean']:10.4f} {r['inv']:7.3f}")
    print("\n(viol should be near/below target 0.05 for well-calibrated methods; DRO trades higher inv for lower viol)")

if __name__=='__main__':
    main()
