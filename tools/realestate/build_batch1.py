#!/usr/bin/env python3
"""Real Estate batch 1: listed-REIT property candidates from SEC 10-K property tables.

Sources (US federal filings, fetched to a scratch evidence folder):
- BXP, Inc. FY2025 10-K: Schedule III (property, type, city) and the construction/redevelopment table.
- Host Hotels & Resorts FY2025 10-K: Item 2 consolidated hotel table (hotel, US state/country, land-lease
  and part-ownership footnotes), corroborated against Schedule III by name.
- Listings: 10-K cover securities table (dei:TradingSymbol / SecurityExchangeName) AND current SEC
  submissions; a mismatch blocks the company (AvalonBay, Equity Residential/Vivmark).
- City reference points: US Census 2024 Gazetteer places (public domain). City points are
  "approximate" and labelled as city references, never as a building location.

Rules kept from Codex's contract (research/data-centers/phase4/sector_adapter.py):
- Schedule III / Item 2 listing = "reported_group_owner": the company reports it holds the property in its
  consolidated portfolio. Legal title entity, JV share (unless stated) and ground leases are NOT inferred.
  property_title_verified stays false. A fully leased hotel (footnote 2) is "lessee", not owner.
- Investment access: indirect listed-company equity only. Never direct title.
- No rents, yields, valuations, occupancy or returns are carried (cost columns are dropped).
- No imagery: none was rights-cleared and no point is exact (placeholders apply).
Usage: build_batch1.py <scratch evidence dir>
"""
import hashlib, html, json, re, sys
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4'))
from sector_adapter import SCHEMA, validate, digest  # noqa: E402

EV = Path(sys.argv[1]); OUT = ROOT / 'data/realestate/batch1'; OUT.mkdir(parents=True, exist_ok=True)
REC = json.loads((EV / 'receipts.json').read_text()); SUBS = json.loads((EV / 'subs-receipts.json').read_text())
TENK = json.loads((EV / 'tenk.json').read_text())
AS_OF = '2026-11-14'
STATES = {'AL':'Alabama','AZ':'Arizona','CA':'California','CO':'Colorado','CT':'Connecticut','DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','IL':'Illinois','LA':'Louisiana','MA':'Massachusetts','MD':'Maryland','MN':'Minnesota','NJ':'New Jersey','NY':'New York','PA':'Pennsylvania','TX':'Texas','VA':'Virginia','WA':'Washington','OR':'Oregon','NC':'North Carolina','TN':'Tennessee','UT':'Utah','NV':'Nevada'}
COUNTRIES = {'Brazil':'BR','Canada':'CA','Mexico':'MX','Chile':'CL','Australia':'AU','New Zealand':'NZ','United Kingdom':'GB','Spain':'ES','Netherlands':'NL','Germany':'DE','Italy':'IT','Poland':'PL','Sweden':'SE','Belgium':'BE','France':'FR','Japan':'JP','China':'CN','India':'IN'}

class Tables(HTMLParser):
    def __init__(s): super().__init__(); s.tables=[]; s.cur=None; s.row=None; s.cell=None; s.d=0
    def handle_starttag(s,t,a):
        if t=='table':
            s.d+=1
            if s.d==1: s.cur=[]
        elif t=='tr' and s.cur is not None: s.row=[]
        elif t in('td','th') and s.row is not None: s.cell=[]
    def handle_endtag(s,t):
        if t=='table':
            s.d-=1
            if s.d==0 and s.cur is not None: s.tables.append(s.cur); s.cur=None
        elif t=='tr' and s.row is not None:
            r=[c for c in s.row if c]
            if r: s.cur.append(r)
            s.row=None
        elif t in('td','th') and s.cell is not None: s.row.append(re.sub(r'\s+',' ',''.join(s.cell)).strip()); s.cell=None
    def handle_data(s,d):
        if s.cell is not None: s.cell.append(d)

def tables(k):
    p=Tables(); p.feed((EV/'raw'/f'{k}.htm').read_text(encoding='utf-8',errors='replace')); return p.tables
NUM=re.compile(r'^\(?[\d,.]+\)?$|^[—–-]$')
def slug(s): return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',html.unescape(s).lower())).strip('-')[:80]
def tenk_ev(k, locator): r=REC[k]; return {'url':r['url'],'sha256':r['sha256'],'checked_at':r['checked_at'],'locator':locator,'sha256_scope':'source_body'}

# ---------- listings: cover page vs current SEC submissions ----------
def cover(k):
    s=(EV/'raw'/f'{k}.htm').read_text(encoding='utf-8',errors='replace')
    g=lambda n:[html.unescape(re.sub('<[^>]+>','',m)).strip() for m in re.findall(rf'name="dei:{n}"[^>]*>(.*?)</ix:nonNumeric>',s,re.S)]
    return list(zip(g('Security12bTitle'),g('TradingSymbol'),g('SecurityExchangeName')))
MIC={'New York Stock Exchange':'XNYS','The Nasdaq Stock Market LLC':'XNAS'}; SUBX={'NYSE':'XNYS','Nasdaq':'XNAS'}
companies_audit={}; companies={}
for k in TENK:
    cv=cover(k); common=[c for c in cv if re.search(r'common',c[0],re.I)]; sub=SUBS[k]
    cur=dict(zip(sub['tickers'],sub['exchanges']))
    ok=bool(common) and common[0][1] in cur and SUBX.get(cur[common[0][1]])==MIC.get(common[0][2])
    companies_audit[k]={'legal_name':sub['name'],'cik':f"{TENK[k]['cik']:010d}",'cover_common':common[:1],'current_sec_tickers':cur,
        'listing_verified':ok,'filing':REC[k]['url'],'period':TENK[k]['period'],
        'note':'cover ticker matches current SEC submissions' if ok else 'BLOCKED: 10-K cover ticker not in current SEC submissions (renamed, delisted or changed); listing not asserted'}
    if ok:
        t,sym,ex=common[0]; cik=f"{TENK[k]['cik']:010d}"
        companies[f'cik:{cik}']={'identity':{'scheme':'cik','value':cik,'evidence':{'url':sub['url'],'sha256':sub['sha256'],'checked_at':sub['checked_at'],'locator':'SEC company submissions: CIK, legal name, current tickers/exchanges'}},
            'listing':{'name':sub['name'],'ticker':sym,'exchange':MIC[ex],'exchange_mic':MIC[ex],'security_type':'common_equity','evidence':tenk_ev(k,f'10-K cover securities table: {t} / {sym} / {ex}; matched to current SEC submissions')},
            'headquarters':None}

# ---------- city reference points (US Census Gazetteer, public domain) ----------
GZ=EV/'gaz'/'gaz.zip'; GZSHA=hashlib.sha256(GZ.read_bytes()).hexdigest()
gaz={}
for line in (EV/'gaz'/'2024_Gaz_place_national.txt').read_text(encoding='utf-8',errors='replace').splitlines()[1:]:
    c=line.split('\t'); nm=re.sub(r' (city|town|village|CDP|borough|municipality|city and borough|consolidated government \(balance\)|metropolitan government \(balance\)|urban county)$','',c[3].strip())
    gaz.setdefault((c[0],nm.lower()),[]).append((float(c[10]),float(c[11].strip()),c[3].strip(),c[1]))
def city_point(rid, city, st):
    hits=gaz.get((st,city.lower()))
    if hits and len(hits)>1: hits=[h for h in hits if not h[2].endswith(' CDP')]  # incorporated place beats a same-name CDP
    if not hits or len(hits)!=1: return None
    lat,lon,full,geoid=hits[0]
    return {'precision':'approximate','lat':round(lat,5),'lon':round(lon,5),'label':f'{city}, {st} (city reference point, not the building)','basis':'US Census 2024 Gazetteer place internal point for the city named in the filing (public domain)','satellite_allowed':False,
            'evidence':{'url':'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip','sha256':GZSHA,'checked_at':'2026-11-14T02:37:00Z','locator':f'Gazetteer place GEOID {geoid} ({full}, {st}) INTPTLAT/INTPTLONG','sha256_scope':'source_body','record_id':rid,'scope':'city_reference'}}

def reuse(loc_basis):
    sec='Facts extracted from a US SEC 10-K (federal filing; facts only, no tables or prose copied); same SEC scope the owner approved for the Equinix release (#109)'
    return {'fields':{'identity':{'status':'cleared','basis':sec},'status':{'status':'cleared','basis':sec},'economic_relationship':{'status':'cleared','basis':sec},
            'listing':{'status':'cleared','basis':'10-K cover securities table + current SEC submissions'},'location':{'status':'cleared','basis':loc_basis}},'review':{}}

def record(k, rid, name, cc, city, subtype, category, stage, label, loc, exposure, locator, source_id, extra=None):
    ev=tenk_ev(k, locator)
    r={'schema':SCHEMA,'id':rid,'source_identity':{'authority':f'sec.gov:10-K:{k}','id':source_id},'synthetic':False,'name':name,'sector':'real_estate','country_code':cc,'city':city,
       'asset':{'category':category,'subtype':subtype,'parent_id':None,'count_as_project':True,'building_identity_evidence':ev} if category=='building' else {'category':category,'subtype':subtype,'parent_id':None,'count_as_project':True},
       'status':{'stage':stage,'label':label,'as_of':TENK[k]['period'],'certainty':'company_reported'},'location':loc,'identity_evidence':ev,
       'exposures':[{**exposure,'evidence':exposure.get('evidence',ev),'listing':companies[exposure['company_ref']]['listing'],'headquarters':None}],'imagery':[],'verification':{'classification':'company_confirmed','date':AS_OF,'property_title_verified':False},
       'reuse':reuse('US Census Gazetteer (public domain) city point' if loc['precision']!='unknown' else 'No point published'),'preview_only':True}
    if extra: r.update(extra)
    validate(r); return r

def access(scope): return {'type':'listed_REIT','verified':True,'scope':scope}
OWN_NOTE='Indirect listed-REIT equity exposure only; buying shares gives no title to this property'
records=[]; research=[]; rejected=[]

# ---------- BXP ----------
bxp_ref='cik:'+companies_audit['BXP']['cik']
seen=set(); TYPE={'Office':'Office','Residential':'Residential portfolio property','Retail':'Retail','Hotel':'Hotel','Laboratory/Life Sciences':'Laboratory / life sciences','Land':'Land','Garage':'Parking','Parking':'Parking'}
for t in tables('BXP'):
    head=' '.join(' '.join(r) for r in t[:4])
    if 'Schedule 3' not in head or 'Location' not in head: continue
    for r in t:
        c=[x for x in r if x!='$']
        if len(c)<14 or c[0] in ('Property Name','Land') or not re.match(r'^[A-Za-z .\'-]+, [A-Z]{2}$',c[2]): continue
        name,typ,locn=c[0],c[1],c[2]; nums=c[3:]
        try: bldg=nums[5]; landheld=nums[6]; dev=nums[7]
        except IndexError: continue
        sid=slug(name)
        if sid in seen: continue
        seen.add(sid); rid=f're:bxp:{sid}'; city,st=locn.rsplit(', ',1)
        if typ=='Land' or (bldg in ('—','-') and dev in ('—','-')):
            research.append({'id':rid,'company':'BXP','name':name,'location':locn,'reason':'Land / land held for development in Schedule III; no building or project milestone evidenced'}); continue
        loc=city_point(rid,city,st) or {'precision':'unknown','lat':None,'lon':None,'label':f'{locn}; no unique city reference point','satellite_allowed':False}
        stage,label=(('operating','In-service property: building cost depreciated in Schedule III at 31 Dec 2025') if dev in ('—','-') else ('unknown','Schedule III carries development/construction-in-progress cost at 31 Dec 2025; milestone not stated'))
        exp={'role':'reported_group_owner','label':'Held in the company\'s consolidated real estate (Schedule III)','relationship_scope':'Company-reported consolidated holding of this named property; holding entity, joint-venture share and ground leases not established','property_stake':None,'company_ref':bxp_ref,'investment_access':access(OWN_NOTE)}
        records.append(record('BXP',rid,name,'US',city,TYPE.get(typ,typ),'existing_asset',stage,label,loc,exp,f'Schedule III row: {name} | {typ} | {locn}',sid))
# construction / redevelopment table (status + stated ownership share)
for t in tables('BXP'):
    if not t or not any('Construction/Redevelopment Properties' in ' '.join(r) for r in t[:3]): continue
    for r in t:
        c=[x for x in r if x not in('$','%')]
        if len(c)<5 or not re.match(r'^Q\d \d{4}$',c[1]) or not re.match(r'.+, [A-Z]{2}$',c[2]): continue
        raw=c[0]; m=re.search(r'\(([\d.]+)% ownership\)',raw); stake=float(m.group(1)) if m else None
        name=re.sub(r'\s*\((Redevelopment|[\d.]+% ownership|\d+ units|\d+ Units)\)','',raw).strip(); redev='Redevelopment' in raw
        sid=slug(name); rid=f're:bxp:{sid}'; city,st=c[2].rsplit(', ',1)
        records=[x for x in records if x['id']!=rid]
        loc=city_point(rid,city,st) or {'precision':'unknown','lat':None,'lon':None,'label':f'{c[2]}; no unique city reference point','satellite_allowed':False}
        ev=tenk_ev('BXP',f'Construction/Redevelopment table row: {raw} | estimated stabilization {c[1]} | {c[2]}')
        exp={'role':'developer','label':'Company-reported developer of this construction/redevelopment project','relationship_scope':'Named project in the company\'s construction/redevelopment table'+(f'; company-stated {stake:g}% ownership of this property' if stake else '; ownership share not stated (treated as not established)'),
             'property_stake':stake,'company_ref':bxp_ref,'investment_access':access(OWN_NOTE)}
        if stake is not None: exp.update(stake_scope='specific_property',property_evidence={**ev,'record_id':rid,'scope':'specific_property'})
        records.append(record('BXP',rid,name,'US',city,'Redevelopment' if redev else 'Development','project','under_construction',f'Under {"redevelopment" if redev else "construction"}; company-estimated stabilization {c[1]} (target, not a milestone)',loc,exp,ev['locator'],sid+':development'))

# ---------- Host Hotels ----------
hst_ref='cik:'+companies_audit['HST']['cik']; sched={slug(r[0]) for t in tables('HST') for r in t if len(r)>8}
def hst_items(row):
    out=[]; i=0
    while i<len(row):
        if i+1<len(row) and NUM.match(row[i+1]): out.append(('hotel',row[i],row[i+1])); i+=2
        else: out.append(('region',row[i],None)); i+=1
    return out
regions=['',''] ; hotels=[]
TH=tables('HST'); i0=next(i for i,t in enumerate(TH) if t and t[0][:2]==['Location','Rooms'])
for t in (TH[i0][1:], TH[i0+1]):  # the hotel table continues in the next table ("(cont.)" headers)
    for r in t:
        items=hst_items(r)
        for j,(kind,a,b) in enumerate(items[:2]):
            col=j if len(items)>1 else 0
            if a.startswith('Total'): continue
            if kind=='region': regions[col]=re.sub(r'\s*\(cont\.\)','',a)
            else: hotels.append((a,regions[col],b))
for raw,region,rooms in hotels:
    SUP={'¹':'1','²':'2','³':'3'}; marks={SUP[m] for m in re.findall('⁽([¹²³])⁾',raw)}; name=re.sub(r'\s*⁽[¹²³]⁾','',raw).strip(); sid=slug(name); rid=f're:hst:{sid}'
    cc='US' if region in STATES.values() or region=='Washington, D.C.' else COUNTRIES.get(region)
    if not cc: rejected.append({'id':rid,'name':name,'reason':f'Region "{region}" not mapped to a country'}); continue
    corroborated=sid in sched or any(len(s)>=8 and (sid.startswith(s) or s.startswith(sid)) for s in sched)
    if '2' in marks:
        role,lab,scope=('lessee','Company-reported lessee (land, building and improvements leased from a third party)','Company leases this hotel under a long-term lease; it does not report owning it')
    else:
        role,lab='reported_group_owner','Consolidated hotel reported in the company\'s portfolio'
        scope='Company-reported consolidated hotel'+('; land leased from a third party (ground lease)' if '1' in marks else '')+('; not wholly owned, share not stated' if '3' in marks else '')+'; holding entity not established'
    exp={'role':role,'label':lab,'relationship_scope':scope,'property_stake':None,'company_ref':hst_ref,'investment_access':access(OWN_NOTE)}
    loc={'precision':'unknown','lat':None,'lon':None,'label':f'{region}{", United States" if cc=="US" else ""} (filing gives state/country only)','satellite_allowed':False}
    records.append(record('HST',rid,name,cc,None,'Hotel','existing_asset','operating',f'Consolidated hotel as of 20 Feb 2026 ({rooms} rooms, company-reported)',loc,exp,
        f'Item 2 consolidated hotels table: {name} | {region} | {rooms} rooms'+(' | footnote '+','.join(sorted(marks)) if marks else ''),sid,
        {'corroboration':{'schedule_iii_name_match':corroborated}}))

# ---------- tiers ----------
dups={};
for r in records: dups.setdefault(r['id'],[]).append(r)
assert all(len(v)==1 for v in dups.values()), [k for k,v in dups.items() if len(v)>1]
eligible=[r for r in records if all(f['status']=='cleared' for f in r['reuse']['fields'].values())]
companies_used={e['company_ref'] for r in records for e in r['exposures']}
env={'schema':'investedia.projects.import.v1','synthetic':False,'companies':{k:v for k,v in companies.items() if k in companies_used},'records':sorted(records,key=lambda r:r['id'])}
(OUT/'import-batch1.json').write_text(json.dumps(env,indent=1,ensure_ascii=False))
(OUT/'research-candidates.json').write_text(json.dumps(research,indent=1,ensure_ascii=False))
(OUT/'rejected.json').write_text(json.dumps(rejected,indent=1,ensure_ascii=False))
(OUT/'companies-audit.json').write_text(json.dumps(companies_audit,indent=1,ensure_ascii=False))
from collections import Counter
st={'records':len(records),'by_company':Counter(r['id'].split(':')[1] for r in records),'by_country':Counter(r['country_code'] for r in records),'by_subtype':Counter(r['asset']['subtype'] for r in records),
    'by_stage':Counter(r['status']['stage'] for r in records),'by_role':Counter(r['exposures'][0]['role'] for r in records),'precision':Counter(r['location']['precision'] for r in records),
    'with_stated_stake':sum(r['exposures'][0]['property_stake'] is not None for r in records),'ground_lease':sum('land leased' in r['exposures'][0]['relationship_scope'] for r in records),
    'not_wholly_owned':sum('not wholly owned' in r['exposures'][0]['relationship_scope'] for r in records),'hst_schedule_iii_corroborated':sum(r.get('corroboration',{}).get('schedule_iii_name_match',False) for r in records),
    'reuse_cleared_awaiting_owner_review':len(eligible),'research_candidates':len(research),'rejected':len(rejected),'imagery':0}
(OUT/'stats.json').write_text(json.dumps(st,indent=1,default=dict))
print(json.dumps(st,indent=1,default=dict))
