import openpyxl, os, json
from collections import defaultdict
COAL={'BIT','SUB','RC','LIG','ANT','SGC','SC','WC'}
def num(v):
    try: return float(v) if v is not None else None
    except: return None

def find_header(ws, needle='Plant Id', maxscan=12):
    """Return (header_row_idx, col_offset) tolerant to schema drift."""
    for i, r in enumerate(ws.iter_rows(min_row=1, max_row=maxscan, values_only=True)):
        vals=[str(c).strip() if c is not None else '' for c in r]
        if needle in vals:
            return i, vals.index(needle)
    return None, None

def colmap(ws, hrow):
    r = list(ws.iter_rows(min_row=hrow+1, max_row=hrow+1, values_only=True))[0]
    return {str(c).replace('\n',' ').strip(): j for j,c in enumerate(r) if c is not None}

def parse_year(y):
    fn=f'sched2345_{y}.xlsx'
    wb=openpyxl.load_workbook(fn, read_only=True)
    # Page 1 consumption
    ws=wb['Page 1 Generation and Fuel Data']
    h,off=find_header(ws,'Plant Id')
    cm=colmap(ws,h)
    def C(name): return cm.get(name)
    ci_plant=C('Plant Id'); ci_ft=C('Reported Fuel Type Code'); ci_unit=C('Physical Unit Label'); ci_freq=C('Respondent Frequency')
    ci_q1=C('Quantity January')
    cons=defaultdict(lambda:[0.0]*12); freq={}
    for r in ws.iter_rows(min_row=h+2, values_only=True):
        if ci_plant>=len(r) or r[ci_plant] is None or not str(r[ci_plant]).strip().isdigit(): continue
        if str(r[ci_ft]).strip() not in COAL: continue
        if str(r[ci_unit]).strip()!='short tons': continue
        p=str(r[ci_plant]).strip(); freq[p]=str(r[ci_freq]).strip() if ci_freq is not None and ci_freq<len(r) and r[ci_freq] is not None else '?'
        for i in range(12):
            v=num(r[ci_q1+i]); cons[p][i]+=(v or 0.0)
    # Page 2 coal stocks
    ws=wb['Page 2 Coal Stocks Data']
    h,off=find_header(ws,'Plant Id')
    cm=colmap(ws,h)
    ci_plant=cm.get('Plant Id'); ci_ft=cm.get('Reported Fuel Type Code'); ci_unit=cm.get('Physical Unit Label')
    ci_q1=cm.get('Quantity January')
    st=defaultdict(lambda:[None]*12)
    for r in ws.iter_rows(min_row=h+2, values_only=True):
        if ci_plant>=len(r) or r[ci_plant] is None or not str(r[ci_plant]).strip().isdigit(): continue
        if str(r[ci_unit]).strip()!='short tons': continue
        p=str(r[ci_plant]).strip()
        for i in range(12):
            v=num(r[ci_q1+i])
            if v is not None:
                st[p][i]=(st[p][i] or 0.0)+v
    # Page 5 receipts
    ws=wb['Page 5 Fuel Receipts and Costs']
    h,off=find_header(ws,'Plant Id')
    cm=colmap(ws,h)
    ci_plant=cm.get('Plant Id'); ci_month=cm.get('MONTH'); ci_grp=cm.get('FUEL_GROUP'); ci_qty=cm.get('QUANTITY'); ci_ptype=cm.get('Purchase Type')
    rec=defaultdict(lambda:[0.0]*12); ptype=defaultdict(lambda:defaultdict(int))
    for r in ws.iter_rows(min_row=h+2, values_only=True):
        if ci_plant>=len(r) or r[ci_plant] is None or not str(r[ci_plant]).strip().isdigit(): continue
        if str(r[ci_grp]).strip()!='Coal': continue
        try: m=int(r[ci_month])
        except: continue
        p=str(r[ci_plant]).strip()
        rec[p][m-1]+=(num(r[ci_qty]) or 0.0)
        if ci_ptype is not None and r[ci_ptype] is not None:
            ptype[p][str(r[ci_ptype]).strip()]+=1
    wb.close()
    return cons, st, freq, rec, ptype

# Build full panel keyed by (plant, year, month)
panel={}
for y in range(2015,2025):
    cons,st,freq,rec,ptype=parse_year(y)
    mf=[p for p in st if p in cons and freq.get(p)=='M']
    for p in mf:
        for i in range(12):
            panel[(p,y,i+1)]=dict(stock=st[p][i], burn=cons[p][i], recv=rec[p][i])
    print(f'{y}: monthly-filer coal plants={len(mf)}, plant-months={len(mf)*12}')

json.dump({f'{k[0]}|{k[1]}|{k[2]}':v for k,v in panel.items()},
          open('coal_panel_2015_2024.json','w'))
print('TOTAL panel plant-months:', len(panel))
print('unique plants:', len({k[0] for k in panel}))
