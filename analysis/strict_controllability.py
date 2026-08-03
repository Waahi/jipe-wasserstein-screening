import json, numpy as np, pandas as pd
from collections import defaultdict
raw=json.load(open('coal_panel_2015_2024.json'))
P=defaultdict(list)
for k,v in raw.items():
    p,y,m=k.split('|'); P[p].append((int(y),int(m),v['stock'],v['burn'],v['recv']))
for p in P: P[p].sort()
def nextm(y,m): return (y+1,1) if m==12 else (y,m+1)

# Build tidy panel with HISTORY-ONLY burn forecast (seasonal-naive: same month last year; fallback trailing-12 mean)
rows=[]
for p,seq in P.items():
    idx={(y,m):i for i,(y,m,s,b,r) in enumerate(seq)}
    burns={(y,m):(b if b else 0.0) for (y,m,s,b,r) in seq}
    for i,(y,m,s,b,r) in enumerate(seq):
        if s is None: continue
        # history-only forecast of NEXT month burn d_hat_{t+1}
        yN,mN=nextm(y,m)
        # seasonal naive: burn at (yN-1, mN); fallback trailing-12 mean up to t
        dhat=None
        if (yN-1,mN) in burns and burns[(yN-1,mN)]>0:
            dhat=burns[(yN-1,mN)]
        else:
            hist=[burns[(yy,mm)] for (yy,mm) in burns if (yy<y or (yy==y and mm<=m)) and burns[(yy,mm)]>0]
            if len(hist)>=6: dhat=np.mean(hist[-12:])
        if not dhat or dhat<=0: continue
        # realized next-month values
        if (yN,mN) not in idx: continue
        j=idx[(yN,mN)]
        r_next=seq[j][4] or 0.0        # receipts next month (response)
        d_real_next=seq[j][3] or 0.0   # realized next-month burn (innovation control)
        r_lag=r or 0.0                 # current-month receipts (lagged-receipts control)
        # inventory GAP vs a 30-day target on the HISTORY-ONLY forecast
        gap = s - 30.0*(dhat/30.0)     # = s - dhat  (stock minus one-month expected burn); keep interpretable
        rows.append(dict(plant=p, ym=f'{y}-{m:02d}', y=y, m=m,
                         r_next=r_next, gap=gap, dhat=dhat, r_lag=r_lag, d_real_next=d_real_next,
                         mb=None))
df=pd.DataFrame(rows)
# normalize flows by plant mean burn (scale-free)
mb=df.groupby('plant')['dhat'].transform('mean')
df['r_next_n']=df['r_next']/mb
df['gap_n']=df['gap']/mb
df['dhat_n']=df['dhat']/mb
df['r_lag_n']=df['r_lag']/mb
df['dinnov_n']=(df['d_real_next']-df['dhat'])/mb   # realized-burn innovation (history-orthogonal shock)
df=df.replace([np.inf,-np.inf],np.nan).dropna(subset=['r_next_n','gap_n','dhat_n','r_lag_n','dinnov_n'])
print(f'N obs={len(df)}, plants={df.plant.nunique()}, months={df.ym.nunique()}')

import statsmodels.formula.api as smf
# plant FE + calendar-time FE (absorb via C()), cluster by plant
# Hypothesis: coef on gap_n < 0 (bigger gap = more cushion = FEWER next receipts), stable after controls
m1=smf.ols('r_next_n ~ gap_n', data=df).fit(cov_type='cluster', cov_kwds={'groups':df['plant']})
m2=smf.ols('r_next_n ~ gap_n + dhat_n + r_lag_n + dinnov_n', data=df).fit(cov_type='cluster', cov_kwds={'groups':df['plant']})
m3=smf.ols('r_next_n ~ gap_n + dhat_n + r_lag_n + dinnov_n + C(plant) + C(ym)', data=df).fit(cov_type='cluster', cov_kwds={'groups':df['plant']})
def show(m,tag):
    b=m.params.get('gap_n'); se=m.bse.get('gap_n'); t=b/se; p=m.pvalues.get('gap_n')
    print(f'{tag:42s} gap_n coef={b:+.4f}  se={se:.4f}  t={t:+.2f}  p={p:.2e}')
print('\n=== STRICT controllability: does history-only inventory gap predict NEXT-month receipts? ===')
show(m1,'(1) bivariate')
show(m2,'(2) + dhat + lagged receipts + burn innovation')
show(m3,'(3) + plant FE + calendar-time FE  [FULL]')
print('\nExpected sign NEGATIVE (larger cushion -> fewer receipts). Material & stable across (1)->(3) => gate PASS.')
# effect-size context: a 1-SD gap change
sd=df['gap_n'].std()
b3=m3.params.get('gap_n')
print(f'\n1-SD gap change = {sd:.2f} (normalized); implied receipts change = {b3*sd:+.3f} of mean monthly burn')
