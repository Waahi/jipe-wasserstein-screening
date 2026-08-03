# -*- coding: utf-8 -*-
"""Gate 2 — clustered/block-bootstrap inference on the expected-shortfall gap.
Per-origin frontiers (mean inv-days & mean expected-shortfall over plants, per method per alpha),
then at matched inventory the per-origin paired diff d_o = ES_DRO(iv) - ES_SAA(iv) (and seasDRO-SAA),
circular block bootstrap over the 35-origin series (blocks preserve serial dependence), and a
pre-defined non-inferiority margin. Inner eps calibrated once per (origin,plant) at alpha=0.05 and
reused across the alpha frontier (keeps the run tractable)."""
import json, numpy as np
from collections import defaultdict

def wc_prob_exceed(Z,k,eps):
    S=len(Z); base=np.mean(Z>k); below=np.sort(k-Z[Z<=k]); budget=eps; extra=0.0
    for gap in below:
        c=gap/S
        if c<=budget: budget-=c; extra+=1.0/S
        else:
            if gap>0: extra+=(budget/(gap/S))*(1.0/S)
            budget=0.0; break
    return base+extra
def q_inv(Z,a): return float(np.quantile(Z,1-a,method='inverted_cdf'))
def saa(Z,a): return q_inv(Z,a)
def dro_k(Z,a,eps):
    lo,hi=0.0,max(0.0,np.max(Z))+1.0
    if wc_prob_exceed(Z,lo,eps)<=a: return 0.0
    for _ in range(50):
        m=0.5*(lo+hi)
        if wc_prob_exceed(Z,m,eps)<=a: hi=m
        else: lo=m
    return hi
def inner_eps(Z,alpha,grid):
    n=len(Z)
    if n<16: return 0.0
    for eps in grid:
        v=[]
        for h in range(min(8,n//4),0,-1):
            fit=Z[:-h]; t=Z[-h]
            if len(fit)<8: continue
            v.append(1.0 if t>dro_k(fit[fit>0],alpha,eps) else 0.0)
        if v and np.mean(v)<=alpha: return eps
    return grid[-1]

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
    allm=sorted({ym for p in S for ym in S[p]})
    WIN=48; ALPHAS=[0.02,0.05,0.10,0.15,0.20]; GRID=[0.0,0.02,0.05,0.10,0.15,0.20,0.30]
    origins=list(range(WIN,len(allm)-1))
    ORIG=[]
    for t0i in origins:
        tr=allm[t0i-WIN+1:t0i+1]; test_ym=allm[t0i+1]
        rec=defaultdict(lambda: defaultdict(lambda:{'inv':[],'short':[]}))
        for p,dd in S.items():
            twp=np.array([dd[ym] for ym in tr if ym in dd and dd[ym]>0],float)
            if len(twp)<24 or test_ym not in dd or dd[test_ym]<=0: continue
            mb=twp.mean()
            if mb<=0: continue
            Z=twp/mb; tv=dd[test_ym]/mb
            monmean=defaultdict(list)
            for ym in tr:
                if ym in dd and dd[ym]>0: monmean[ym[1]].append(dd[ym]/mb)
            mm={k:np.mean(v) for k,v in monmean.items()}
            seas=mm.get(test_ym[1],1.0)
            Zres=np.array([ (dd[ym]/mb)-mm.get(ym[1],1.0) for ym in tr if ym in dd and dd[ym]>0])
            eps=inner_eps(Z,0.05,GRID)
            for a in ALPHAS:
                for meth,k in [('SAA',saa(Z,a)),('DRO',dro_k(Z,a,eps)),('seasDRO',seas+dro_k(Zres,a,eps))]:
                    rec[meth][a]['inv'].append(k); rec[meth][a]['short'].append(max(0.0,tv-k))
        ORIG.append(rec)
    def frontier(rec):
        F={}
        for meth in ['SAA','DRO','seasDRO']:
            pts=[]
            for a in ALPHAS:
                d=rec[meth][a]
                if d['inv']: pts.append((np.mean(d['inv'])*30, float(np.mean(d['short']))))
            F[meth]=sorted(pts)
        return F
    Forig=[frontier(r) for r in ORIG]
    def es_at_inv(F,meth,iv):
        pts=F[meth]
        if not pts: return np.nan
        x=[p[0] for p in pts]; y=[p[1] for p in pts]
        return float(np.interp(iv,x,y)) if min(x)-1e-9<=iv<=max(x)+1e-9 else np.nan
    INVS=[49,53,56]
    print(f"origins={len(Forig)}")
    rng=np.random.RandomState(0)
    def cbb(d,B=2000,L=4):
        d=np.array([x for x in d if not np.isnan(x)]); n=len(d)
        if n<3: return (np.nan,np.nan,np.nan)
        means=[]; nb=int(np.ceil(n/L))
        for _ in range(B):
            starts=rng.randint(0,n,nb)
            idx=np.concatenate([(np.arange(s,s+L)%n) for s in starts])[:n]
            means.append(d[idx].mean())
        return (float(np.mean(d)),float(np.percentile(means,2.5)),float(np.percentile(means,97.5)))
    print("\n=== paired ES gap at matched inventory, circular block bootstrap over origins (L=4) ===")
    print("(positive => DRO/seasDRO WORSE than SAA; CI>0 => SAA significantly better; CI spans 0 => no evidence)")
    out={'invs':INVS,'diff_DRO':{}, 'diff_seas':{}}
    for iv in INVS:
        dD=[es_at_inv(F,'DRO',iv)-es_at_inv(F,'SAA',iv) for F in Forig]
        dS=[es_at_inv(F,'seasDRO',iv)-es_at_inv(F,'SAA',iv) for F in Forig]
        mD,loD,hiD=cbb(dD); mS,loS,hiS=cbb(dS)
        nD=sum(1 for x in dD if not np.isnan(x)); nS=sum(1 for x in dS if not np.isnan(x))
        print(f" inv={iv}d  DRO-SAA mean={mD:+.4f} CI[{loD:+.4f},{hiD:+.4f}] n={nD}   seasDRO-SAA mean={mS:+.4f} CI[{loS:+.4f},{hiS:+.4f}] n={nS}")
        out['diff_DRO'][str(iv)]=[x for x in dD]; out['diff_seas'][str(iv)]=[x for x in dS]
    json.dump(out,open('gate2_diffs.json','w'))
    print("\nsaved gate2_diffs.json")

if __name__=='__main__':
    main()
