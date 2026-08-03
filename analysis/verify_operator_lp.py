# -*- coding: utf-8 -*-
"""Independent LP verification of the greedy Wasserstein worst-case-exceedance operator (Codex D-i).
Worst-case P(Z>k) over W1 ball radius eps, primal transport LP:
  max  base + sum_{i: z_i<=k} x_i/S     (mass fraction of atom i pushed just above k)
  s.t. sum_{i: z_i<=k} x_i*(k - z_i)/S <= eps ;  0<=x_i<=1
LP allows FRACTIONAL transport; the greedy operator moves whole atoms only. Compare."""
import numpy as np
from scipy.optimize import linprog

def wc_prob_exceed_greedy(Z, k, eps):
    S=len(Z); base=np.mean(Z>k)
    below=np.sort(k-Z[Z<=k]); budget=eps; moved=0
    for gap in below:
        cost=gap/S
        if cost<=budget: budget-=cost; moved+=1
        else: break
    return base+moved/S

def wc_prob_exceed_lp(Z, k, eps):
    Z=np.asarray(Z,float); S=len(Z)
    base=np.mean(Z>k)
    idx=np.where(Z<=k)[0]
    if len(idx)==0: return base
    gaps=(k-Z[idx])/S              # per-unit transport cost coefficient
    c=-np.ones(len(idx))/S         # maximize sum x_i/S  ->  minimize -sum x_i/S
    A_ub=[gaps]; b_ub=[eps]
    res=linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=[(0,1)]*len(idx), method='highs')
    if not res.success: return np.nan
    return base + (-res.fun)

def wc_prob_exceed_greedy_frac(Z, k, eps):
    """Greedy WITH fractional last atom (candidate fix)."""
    S=len(Z); base=np.mean(Z>k)
    below=np.sort(k-Z[Z<=k]); budget=eps; extra=0.0
    for gap in below:
        cost=gap/S
        if cost<=budget: budget-=cost; extra+=1.0/S
        else:
            if gap>0: extra += (budget/(gap/S))*(1.0/S)   # fractional move of last atom
            budget=0; break
    return base+extra

rng=np.random.RandomState(0)
cases=[]
# assorted small samples incl. ties and integer alpha*S
cases.append(("iid-exp n=12", np.round(rng.exponential(1.0,12),3)))
cases.append(("with-ties",   np.array([0.5,0.5,0.5,1.0,1.0,2.0,2.0,2.0,3.0,5.0])))
cases.append(("uniform n=20", np.round(rng.uniform(0,3,20),3)))
maxdiff_g=maxdiff_f=0.0
print(f"{'case':16s} {'k':>5s} {'eps':>5s} {'greedy':>8s} {'greedy+frac':>11s} {'LP(exact)':>10s} {'g-LP':>8s} {'f-LP':>8s}")
for name,Z in cases:
    for k in [np.percentile(Z,60), np.median(Z), np.percentile(Z,80)]:
        for eps in [0.0, 0.03, 0.1, 0.25]:
            g=wc_prob_exceed_greedy(Z,k,eps)
            f=wc_prob_exceed_greedy_frac(Z,k,eps)
            lp=wc_prob_exceed_lp(Z,k,eps)
            maxdiff_g=max(maxdiff_g,abs(g-lp)); maxdiff_f=max(maxdiff_f,abs(f-lp))
            flag = '' if abs(g-lp)<1e-9 else '  <-- greedy != LP'
            print(f"{name:16s} {k:5.2f} {eps:5.2f} {g:8.4f} {f:11.4f} {lp:10.4f} {g-lp:+8.4f} {f-lp:+8.4f}{flag}")
print(f"\nMAX |greedy - LP|      = {maxdiff_g:.4f}")
print(f"MAX |greedy+frac - LP| = {maxdiff_f:.4f}")
print("\nIf greedy != LP but greedy+frac == LP: the operator needs the fractional last-atom move.")
