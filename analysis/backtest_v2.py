# -*- coding: utf-8 -*-
"""Step 5c-v2 — fixes the two Codex-flagged design flaws.
(1) ORTHOGONAL surge definitions (independent of forecastQ's predictor):
      - calendar-peak: Jan,Feb,Jul,Aug (frozen)
      - realized-quantile: test-month realized burn >= p80 of plant's training-window demand
        (post-hoc stratification ONLY; enters no model)
(2) FAIR DRO frontier:
      - all methods traced over the SAME conservativeness family = target alpha grid
      - DRO at each alpha uses INNER-rolling-calibrated epsilon (not an exogenous eps sweep)
      - add seasonal-conditional DRO: W1 on de-seasonalized residuals
Metrics: pooled + both orthogonal tails; realized violation vs inventory per method.
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

def q_inv(Z,a): return float(np.quantile(Z,1-a,method='inverted_cdf'))
def saa(Z,a):   return q_inv(Z,a)
def dro_k(Z,alpha,eps):
    lo,hi=0.0,max(0.0,np.max(Z))+1.0
    if wc_prob_exceed(Z,lo,eps)<=alpha: return 0.0
    for _ in range(60):
        mid=0.5*(lo+hi)
        if wc_prob_exceed(Z,mid,eps)<=alpha: hi=mid
        else: lo=mid
    return hi

def inner_eps(Z, alpha, eps_grid):
    """smallest eps whose inner rolling-origin OOS violation <= alpha (leave-last-h-out inside train)."""
    n=len(Z)
    if n<16: return 0.0
    for eps in eps_grid:
        viol=[]
        for h in range(min(8,n//4),0,-1):
            fit=Z[:-h]; test=Z[-h]
            if len(fit)<8: continue
            k=dro_k(fit[fit>0],alpha,eps)
            viol.append(1.0 if test>k else 0.0)
        if viol and np.mean(viol)<=alpha:
            return eps
    return eps_grid[-1]

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
    WIN=48; ALPHAS=[0.02,0.05,0.10,0.15,0.20]; EPSGRID=[0.0,0.02,0.05,0.10,0.15,0.20,0.30]
    PEAK={1,2,7,8}
    origins=list(range(WIN,len(allmonths)-1))

    # rec[scope][method][alpha] -> lists
    def newrec(): return defaultdict(lambda: defaultdict(lambda: defaultdict(lambda:{'viol':[],'inv':[],'short':[]})))
    R=newrec()
    n=dict(pooled=0, cal=0, rq=0)
    for t0i in origins:
        train_ms=allmonths[t0i-WIN+1:t0i+1]; test_ym=allmonths[t0i+1]
        for p,dd in S.items():
            twp=np.array([dd[ym] for ym in train_ms if ym in dd and dd[ym]>0],float)
            if len(twp)<24 or test_ym not in dd or dd[test_ym]<=0: continue
            mb=twp.mean()
            if mb<=0: continue
            Z=twp/mb; test_val=dd[test_ym]/mb
            # de-seasonalized residual demand for seasonal-DRO: subtract calendar-month mean (train-only)
            monmean={}
            for ym in train_ms:
                if ym in dd and dd[ym]>0:
                    monmean.setdefault(ym[1],[]).append(dd[ym]/mb)
            mm={k:np.mean(v) for k,v in monmean.items()}
            seas_test = mm.get(test_ym[1], 1.0)
            Zres = np.array([ (dd[ym]/mb) - mm.get(ym[1],1.0) for ym in train_ms if ym in dd and dd[ym]>0 ])
            # orthogonal surge flags
            is_cal = test_ym[1] in PEAK
            p80 = np.quantile(twp,0.80)
            is_rq = dd[test_ym] >= p80         # realized, post-hoc only
            n['pooled']+=1; n['cal']+=is_cal; n['rq']+=is_rq
            # epsilon inner-calibrated per alpha
            for a in ALPHAS:
                eps_a = inner_eps(Z, a, EPSGRID)
                ks = {
                    'SAA': saa(Z,a),
                    'DRO': dro_k(Z,a,eps_a),
                    'seasDRO': seas_test + dro_k(Zres+0.0, a, eps_a),  # target = seasonal mean + robust residual quantile
                }
                for meth,k in ks.items():
                    v=1.0 if test_val>k else 0.0
                    for scope,flag in [('pooled',True),('cal',is_cal),('rq',is_rq)]:
                        if flag:
                            R[scope][meth][a]['viol'].append(v); R[scope][meth][a]['inv'].append(k)
                            R[scope][meth][a]['short'].append(max(0.0, test_val-k))
    print(f"origins={len(origins)} pooled={n['pooled']} calendar-peak={n['cal']} ({n['cal']/n['pooled']*100:.1f}%) realized-q80={n['rq']} ({n['rq']/n['pooled']*100:.1f}%)")
    out={}
    for scope in ['pooled','cal','rq']:
        print(f"\n===== {scope} =====  (inv days / realized viol, per alpha; DRO eps inner-calibrated)")
        out[scope]={}
        for meth in ['SAA','DRO','seasDRO']:
            out[scope][meth]={}
            print(f"  {meth}:")
            for a in ALPHAS:
                d=R[scope][meth][a]
                if not d['viol']: continue
                iv=np.mean(d['inv'])*30; vl=np.mean(d['viol'])
                sh=np.array(d['short']); vv=np.array(d['viol'])
                exp_short=float(sh.mean())                       # unconditional expected shortfall (mean-burn units)
                cond_short=float(sh[vv>0].mean()) if (vv>0).any() else 0.0  # severity GIVEN a violation
                out[scope][meth][str(a)]={'inv_days':iv,'viol':vl,'exp_short':exp_short,'cond_short':cond_short,'n':len(d['viol'])}
                print(f"    a={a:<5} inv={iv:6.1f}d  viol={vl:.3f}  Eshort={exp_short:.4f}  cond_short={cond_short:.4f}  n={len(d['viol'])}")
    json.dump(out,open('frontier_v2.json','w'),indent=1)
    print("\nsaved frontier_v2.json")

if __name__=='__main__':
    main()
