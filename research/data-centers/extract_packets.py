"""Re-extract minimal source facts from locally saved official responses; no network or publication.
Raw downloads and the initial selected-source list are private/ignored. The committed
source-packets.json is the offline reproducibility fixture, not a reusable public feed.
"""
import importlib.util,json,re,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('dc',root/'build.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
pack={}
def add(key,facts,receipt=None):
 if receipt is None:receipt=json.loads((root/'sources'/f'{key}.receipt.json').read_text())
 pack[key]={'facts':facts,'facts_sha256':hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'receipt':receipt}
fields=['title','node_id','country','metro','field_address_location','field_latitude','field_longitude','field_utility_power_capacity']
sel=json.loads((root/'selected-source-facilities.json').read_text());add('selected',[{'node_id':s['node_id'],'title':s['title']} for s in sel],json.loads((root/'sources/dlr-global.receipt.json').read_text()))
add('directory-count',{'count':len(m.nextdata((root/'sources/dlr-global.html').read_text())['facilities'])},json.loads((root/'sources/dlr-global.receipt.json').read_text()))
for r in sel:
 key=str(r['node_id']);s=(root/'sources'/f'{key}.html').read_text();d=m.nextdata(s);add(key,{k:d[k] for k in fields if k in d})
for code in ['dc2','sv1','dx1']:
 key='eqix-'+code;s=(root/'sources'/f'{key}.html').read_text();d={}
 for field in ['longitude','latitude','address1','address2','city','country']:
  mat=re.search(r'const '+field+r'\s*=\s*("(?:[^"\\]|\\.)*")',s);d[field]=json.loads(re.sub(r'\\x([0-9a-fA-F]{2})',lambda m:r'\u00'+m.group(1),mat.group(1))) if mat else None
 add(key,d)
for sym in ['EQIX','DLR','AMT']:
 s=(root/'sources'/f'{sym}-10k.html').read_text();cover=[]
 for tr in re.findall(r'<tr\b[^>]*>.*?</tr>',s,re.S|re.I):
  tags={k:[m.clean(v) for v in re.findall(r'<ix:nonNumeric\b[^>]*name="dei:'+k+r'"[^>]*>(.*?)</ix:nonNumeric>',tr,re.S|re.I)] for k in ['Security12bTitle','TradingSymbol']}
  if sym in tags['TradingSymbol'] and any(re.search(r'\bCommon Stock\b',v,re.I) for v in tags['Security12bTitle']) and len(tags['TradingSymbol'])==1:cover.append(tr)
 add(sym+'-10k',{'common_stock_cover_html':''.join(cover)})
 sub=json.loads((root/'sources'/f'{sym}-submissions.html').read_text());r=sub['filings']['recent'];i=next(i for i,f in enumerate(r['form']) if f=='10-K');add(sym+'-submissions',{'filings':{'recent':{k:[v[i]] for k,v in r.items()}}})
sec=json.loads((root/'sources/sec.html').read_text());add('sec',{'fields':sec['fields'],'data':[row for row in sec['data'] if row[sec['fields'].index('ticker')] in ['EQIX','DLR','AMT']]})
add('coresite-va1',{'facility':'VA1','note':'Official VA1 detail page; no concluded parent/JV chain'})
(root/'source-packets.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
