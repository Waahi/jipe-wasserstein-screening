# -*- coding: utf-8 -*-
"""Step 5: base-stock service-level DRO on EIA-923 coal, reusing the WEEE core math.

Base-stock = the 1/u=0 special case of the WEEE capacity core:
  demand Z   = standardized protection-period coal burn (1.0 = mean-month burn; days = k*30)
  decision k = base-stock target
  service    : P(Z > k) <= alpha
  DRO        : min k  s.t.  sup_{W1(Q,Phat)<=eps} Q(Z>k) <= alpha     (non-degenerate)

Degeneracy tests on REAL coal demand:
  T1  eps=0  =>  dro_chance == saa_service   (exact, via inverted_cdf empirical quantile)
  T2  k_dro nondecreasing in eps
  T3  k_dro != k_saa for some plants          (non-degenerate chance form)
  T4  cost-form DRO base-stock == SAA base-stock (degeneracy transmits to the decision).
      NOTE: the offset identity  sup_{W1<=eps} E[(Z-k)+] = E_emp[(Z-k)+] + eps  is the
      Esfahani-Kuhn theorem (1-Lipschitz loss, support unbounded above). We CITE it; we do not
      pretend to independently 'simulate' it. T4 checks its DECISION consequence numerically.
"""
import json, numpy as np
from collections import defaultdict

# ---------- reused Wasserstein worst-case exceedance operator (WEEE core) ----------
def wc_prob_exceed(Z, k, eps):
    """Worst-case P(Z > k) over W1 ball radius eps; empirical step CDF at eps=0.
    Move sub-threshold atoms (mass 1/S) up across k, cheapest gap first, until budget spent.
    FRACTIONAL last-atom move (verified == transport LP; whole-atom-only under-estimates the
    worst case -> would UNDER-size the base-stock and understate the true violation rate)."""
    S=len(Z); base=np.mean(Z>k)
    below=np.sort(k-Z[Z<=k]); budget=eps; extra=0.0
    for gap in below:
        cost=gap/S
        if cost<=budget:
            budget-=cost; extra+=1.0/S          # ties (gap=0) move at zero cost -> handled here
        else:
            if gap>0: extra += (budget/(gap/S))*(1.0/S)   # fractional move of the last atom
            budget=0.0; break
    return base+extra

def saa_service(Z, alpha):
    # smallest k with EMPIRICAL P(Z>k) <= alpha  ==  wc_prob_exceed(Z,k,0) <= alpha
    # inverted_cdf = empirical-CDF inverse => exactly matches the exceedance definition (T1 exact)
    return float(np.quantile(Z, 1-alpha, method='inverted_cdf'))

def dro_chance(Z, alpha, eps):
    lo=0.0; hi=max(0.0,np.max(Z))+1.0
    if wc_prob_exceed(Z,lo,eps)<=alpha: return 0.0
    for _ in range(80):
        mid=0.5*(lo+hi)
        if wc_prob_exceed(Z,mid,eps)<=alpha: hi=mid
        else: lo=mid
    return hi

# ---------- cost-form (linear hinge) — degenerate by Esfahani-Kuhn; checked at decision level ----------
def emp_hinge(Z,k): return np.mean(np.maximum(Z-k,0.0))
def wc_hinge_unbounded(Z,k,eps):
    # Esfahani-Kuhn analytic identity (theorem), used as-is:
    return emp_hinge(Z,k)+eps
def cost_argmin_k(Z,ratio,eps,grid):
    obj=ratio*grid + np.array([wc_hinge_unbounded(Z,z,eps) for z in grid])
    return grid[int(np.argmin(obj))]

# ---------- build per-plant standardized monthly coal burn = demand Z ----------
raw=json.load(open('coal_panel_2015_2024.json'))
P=defaultdict(list)
for k,v in raw.items():
    p,y,m=k.split('|'); P[p].append((int(y),int(m),v['stock'],v['burn'],v['recv']))
for p in P: P[p].sort()
series={}
for p,seq in P.items():
    b=np.array([x[3] if x[3] else 0.0 for x in seq],float); pos=b[b>0]
    if len(pos)<24: continue
    mb=pos.mean()
    if mb>0: series[p]=b/mb

# ---------- run tests ----------
ALPHA=0.05; EPS=[0.0,0.02,0.05,0.10,0.20]
t1=t2=True; t4_exact=0; ndiff=0; n=0
for p,Zall in series.items():
    Z=Zall[Zall>0]
    if len(Z)<24: continue
    n+=1
    grid=np.linspace(0,np.max(Z)+1.0,2000); gstep=grid[1]-grid[0]
    zsaa=saa_service(Z,ALPHA)
    zc=[dro_chance(Z,ALPHA,e) for e in EPS]
    if abs(zc[0]-zsaa)>1e-6: t1=False
    if any(zc[i+1]<zc[i]-1e-9 for i in range(len(zc)-1)): t2=False
    if abs(zc[-1]-zsaa)>1e-4: ndiff+=1
    if abs(cost_argmin_k(Z,0.3,0.10,grid)-cost_argmin_k(Z,0.3,0.0,grid))<=gstep+1e-12: t4_exact+=1

print(f"Base-stock DRO degeneracy tests on REAL coal demand | alpha={ALPHA} | plants={n}\n")
print(f"T1  eps=0 == SAA (exact)               : {'PASS' if t1 else 'FAIL'}")
print(f"T2  k_dro nondecreasing in eps         : {'PASS' if t2 else 'FAIL'}")
print(f"T3  k_dro != k_saa (some plants)       : {'PASS' if ndiff>0 else 'FAIL'} ({ndiff}/{n} differ at eps=0.20)")
print(f"T4  cost-form DRO k == SAA k           : {t4_exact}/{n} within 1 grid-step")
print(f"    (decision-level degeneracy; the +eps offset identity is Esfahani-Kuhn, cited not simulated)")
print()
p0=max(series, key=lambda p:len(series[p])); Z=series[p0][series[p0]>0]
print(f"Example plant {p0}: base-stock k (mean-burn units; days=k*30)")
print(" eps :", "  ".join(f"{e:.2f}" for e in EPS))
print(" k   :", "  ".join(f"{dro_chance(Z,ALPHA,e):.3f}" for e in EPS), f"| SAA={saa_service(Z,ALPHA):.3f}")
print(" days:", "  ".join(f"{dro_chance(Z,ALPHA,e)*30:.0f}" for e in EPS))
