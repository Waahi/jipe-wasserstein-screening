import urllib.request, json, collections, datetime
from urllib.parse import quote
b='https://services.arcgis.com/BLN4oKB0N1YSgvY8/arcgis/rest/services/CalRecycle_SoildWasteFacilities_SiteActivity/FeatureServer/0/query'
def q(p): return json.loads(urllib.request.urlopen(b+'?'+p, timeout=120).read())
d=q('where='+quote('Cease_Operation IS NOT NULL')+'&outFields=Activity,Cease_Operation,Throughput,ThroughputUnits,Capacity,CapacityUnits&returnGeometry=false&f=json&resultRecordCount=2000')
fs=[f['attributes'] for f in d['features']]
print('total closed w/ cease date pulled:', len(fs))

def cat(a):
    a=(a or '').lower()
    if 'landfill' in a or 'disposal' in a: return 'disposal/landfill'
    if 'transfer' in a or 'processing' in a: return 'transfer/processing'
    if 'compost' in a or 'chipping' in a or 'grinding' in a: return 'compost/green'
    return 'other'

rows=collections.defaultdict(lambda:{'n':0,'y2000':0,'tons_thru':0,'anycap':0,'yrs':collections.Counter()})
for f in fs:
    c=cat(f.get('Activity')); r=rows[c]; r['n']+=1
    ce=f.get('Cease_Operation')
    if ce:
        y=datetime.datetime.fromtimestamp(ce/1000, datetime.timezone.utc).year
        if y>=2000:
            r['y2000']+=1; r['yrs'][y]+=1
    if 'ton' in str(f.get('ThroughputUnits') or '').lower() and (f.get('Throughput') or 0)>0: r['tons_thru']+=1
    if (f.get('Capacity') or 0)>0 and str(f.get('CapacityUnits') or '')!='None': r['anycap']+=1

for c,r in rows.items():
    nyrs=len([y for y in r['yrs'] if y>=2000])
    print("%s: total_closed=%d closed_2000+=%d distinct_2000+_yrs=%d tons_throughput=%d any_capacity_unit=%d"
          % (c, r['n'], r['y2000'], nyrs, r['tons_thru'], r['anycap']))
    print('   yrs2000+:', dict(sorted((y,n) for y,n in r['yrs'].items() if y>=2000)))
