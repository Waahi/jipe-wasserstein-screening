# -*- coding: utf-8 -*-
"""Step 5c — FULL nested rolling-origin backtest (frozen spec).
PRIMARY = all-origin pooled service-inventory frontier per method.
Tail = pre-frozen STRESS estimand: plant x origin origin-known surge (D_hat_{t+1|t} >= p80 of plant's
       48-month training-window demand), classified with origin-known info only.
Methods traced as FRONTIERS (own conservativeness parameter) so dominance is read off the whole curve.
Leakage rules: standardize by train-window mean only; origin-known surge; no test info in any fit.
"""
import json, numpy as np
from collections import defaultdict

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

def q_inv(Z, a):  return float(np.quantile(Z, 1-a, method='inverted_cdf'))
def saa_service(Z, alpha): return q_inv(Z, alpha)
def dro_chance(Z, alpha, eps):
    lo=0.0; hi=max(0.0,np.max(Z))+1.0
    if wc_prob_exceed(Z,lo,eps)<=alpha: return 0.0
    for _ in range(80):
        mid=0.5*(lo+hi)
        if wc_prob_exceed(Z,mid,eps)<=alpha: hi=mid
        else: lo=mid
    return hi
def vanderlaan_ks(Z, alpha, delta=0.10):
    """KS/DKW distributionally-robust service level: worst-case exceedance over the KS band of
    confidence 1-delta = empirical exceedance + dkw. Require <= alpha => empirical <= alpha - dkw.
    If the band is wider than alpha (small-sample regime, dkw>alpha), no interior k guarantees the
    level -> take the most conservative max(Z). (This is a genuine small-sample limitation of the
    type-inf/KS approach vs the continuous W1 ball, NOT a bug.)"""
    n=len(Z); dkw=np.sqrt(np.log(2/delta)/(2*n))
    a_eff=alpha-dkw
    if a_eff<=0: return float(np.max(Z))
    return q_inv(Z, a_eff)

def seasonal_forecast(train_by_ym, allmonths, tw_lo, test_idx):
    """History-only point forecast = same-calendar-month last available train value; else train mean (=1)."""
    ty,tm=allmonths[test_idx]
    for j in range(test_idx-1, tw_lo-1, -1):
        ym=allmonths[j]
        if ym[1]==tm and ym in train_by_ym:
            return train_by_ym[ym]
    return 1.0

def main():
    raw=json.load(open('coal_panel_2015_2024.json'))
    P=defaultdict(list)
    for kk,v in raw.items():
        p,y,m=kk.split('|'); P[p].append((int(y),int(m),v['stock'],v['burn'],v['recv']))
    for p in P: P[p].sort()
    S={}
    for p,seq in P.items():
        b=np.array([x[3] if x[3] else 0.0 for x in seq],float); pos=b[b>0]
        if len(pos)<36: continue
        S[p]={(y,m):bb for (y,m,s,bb,r) in seq}

    allmonths=sorted({ym for p in S for ym in S[p]})
    ALPHA=0.05; WIN=48
    EPS=[0.0,0.02,0.05,0.10,0.15,0.20,0.30]
    ALPHAS=[0.02,0.05,0.10,0.15,0.20]
    DAYS=[15,30,45,60,90]

    origins=list(range(WIN, len(allmonths)-1))
    rec=defaultdict(lambda: defaultdict(lambda: {'viol':[], 'inv':[], 'short':[]}))
    tailrec=defaultdict(lambda: defaultdict(lambda: {'viol':[], 'inv':[], 'short':[]}))
    n_eval=0; n_tail=0
    for t0i in origins:
        tw_lo=t0i-WIN+1
        train_ms=allmonths[tw_lo:t0i+1]
        test_ym=allmonths[t0i+1]
        for p,dd in S.items():
            twp_raw=np.array([dd[ym] for ym in train_ms if ym in dd and dd[ym]>0],float)
            if len(twp_raw)<24: continue
            if test_ym not in dd or dd[test_ym]<=0: continue
            mb=twp_raw.mean()
            if mb<=0: continue
            Z=twp_raw/mb
            test_val=dd[test_ym]/mb
            train_by_ym={ym:(dd[ym]/mb) for ym in train_ms if ym in dd and dd[ym]>0}
            dhat=seasonal_forecast(train_by_ym, allmonths, tw_lo, t0i+1)
            p80=np.quantile(Z,0.80)
            is_surge = dhat>=p80
            resid = Z - 1.0
            n_eval+=1
            if is_surge: n_tail+=1
            def log(method,param,k):
                v=1.0 if test_val>k else 0.0; sh=max(0.0,test_val-k)
                rec[method][param]['viol'].append(v); rec[method][param]['inv'].append(k); rec[method][param]['short'].append(sh)
                if is_surge:
                    tailrec[method][param]['viol'].append(v); tailrec[method][param]['inv'].append(k); tailrec[method][param]['short'].append(sh)
            for a in ALPHAS: log('SAA', a, saa_service(Z,a))
            for e in EPS:    log('DRO', e, dro_chance(Z,ALPHA,e))
            for d in DAYS:   log('fixedDoB', d, d/30.0)
            for a in ALPHAS: log('vdL', a, vanderlaan_ks(Z,a))
            for a in ALPHAS: log('forecastQ', a, dhat + float(np.quantile(resid,1-a,method='inverted_cdf')))

    def summarize(R, tag):
        print(f"\n===== {tag} =====")
        for method in ['SAA','DRO','fixedDoB','vdL','forecastQ']:
            print(f"  {method}:")
            for param in sorted(R[method]):
                d=R[method][param]
                if not d['viol']: continue
                print(f"    param={str(param):<5} inv={np.mean(d['inv'])*30:6.1f}d  viol={np.mean(d['viol']):.3f}  short={np.mean(d['short']):.4f}  n={len(d['viol'])}")
    print(f"outer origins={len(origins)}  pooled evals={n_eval}  surge(tail)={n_tail} ({n_tail/max(n_eval,1)*100:.1f}%)")
    summarize(rec, "POOLED (PRIMARY estimand)")
    summarize(tailrec, "TAIL/STRESS (plant x origin surge, pre-frozen)")

    out={'pooled':{}, 'tail':{}}
    for R,key in [(rec,'pooled'),(tailrec,'tail')]:
        for method in R:
            out[key][method]={str(pm):{'inv_days':float(np.mean(v['inv'])*30),'viol':float(np.mean(v['viol'])),
                                       'short':float(np.mean(v['short'])),'n':len(v['viol'])} for pm,v in R[method].items()}
    json.dump(out, open('frontier_full.json','w'), indent=1)
    print("\nsaved frontier_full.json")

if __name__=='__main__':
    main()
