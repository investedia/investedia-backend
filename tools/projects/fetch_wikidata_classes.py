# Two-step Wikidata fetch used on 11 Nov 2026: list items of one reviewed class (direct P31, with coordinates and an English label,
# best-documented first), then fetch facts in batches of 80. Run from the repo root: python tools/projects/fetch_wikidata_classes.py 1200
import json,sys,time,urllib.request,urllib.parse,re
CLASSES={'wind':('Q194356','Wind energy'),'nuclear':('Q134447','Nuclear energy'),'solar':('Q2298412','Solar energy'),'hydro':('Q15911738','Hydro energy'),'hsr':('Q858485','High-speed rail'),'datacentre':('Q671224','Data centres')}
CAP=int(sys.argv[1])
def sparql(q):
    body=urllib.parse.urlencode({'query':q}).encode()
    for a in range(4):
        try:
            r=urllib.request.Request('https://query.wikidata.org/sparql',data=body,headers={'Accept':'application/sparql-results+json','User-Agent':'InvestediaRobot/1.0 (projects data refresh)'})
            return json.load(urllib.request.urlopen(r,timeout=70))
        except Exception as e: print('retry',e,file=sys.stderr,flush=True);time.sleep(6)
    raise SystemExit('failed')
DETAIL='''SELECT ?item ?itemLabel ?countryLabel ?countryCode ?coord ?alias ?statusLabel ?entry ?inception
 ?capacity ?capacityUnitLabel ?cost ?costUnitLabel ?owner ?ownerLabel ?operator ?operatorLabel
 ?developer ?developerLabel ?contractor ?contractorLabel WHERE { VALUES ?item { %s }
 ?item wdt:P625 ?coord; wdt:P17 ?country. ?country wdt:P297 ?countryCode.
 OPTIONAL { ?item skos:altLabel ?alias FILTER(LANG(?alias)="en") }
 OPTIONAL { ?item wdt:P5817 ?status } OPTIONAL { ?item wdt:P571 ?inception } OPTIONAL { ?item wdt:P729 ?entry }
 OPTIONAL { ?item p:P2109/psv:P2109 ?cq. ?cq wikibase:quantityAmount ?capacity; wikibase:quantityUnit ?capacityUnit }
 OPTIONAL { ?item p:P2130/psv:P2130 ?costq. ?costq wikibase:quantityAmount ?cost; wikibase:quantityUnit ?costUnit }
 OPTIONAL { ?item wdt:P127 ?owner } OPTIONAL { ?item wdt:P137 ?operator }
 OPTIONAL { ?item wdt:P178 ?developer } OPTIONAL { ?item wdt:P1652 ?contractor }
 SERVICE wikibase:label { bd:serviceParam wikibase:language "en" } }'''
for key,(q,t) in CLASSES.items():
    # direct instances with coordinates and an English label; prefer items with more statements (better documented)
    ids=sparql(f'SELECT ?item WHERE {{ ?item wdt:P31 wd:{q}; wdt:P625 ?c; wikibase:statements ?n. ?item rdfs:label ?l FILTER(LANG(?l)="en") }} ORDER BY DESC(?n) LIMIT {CAP}')
    qs=[b['item']['value'].rsplit('/',1)[1] for b in ids['results']['bindings']]
    binds=[];head=None
    for i in range(0,len(qs),80):
        d=sparql(DETAIL%' '.join('wd:'+x for x in qs[i:i+80]));head=d['head'];binds+=d['results']['bindings'];time.sleep(1)
    open(f'data/projects/cache/wikidata-{key}.json','w').write(json.dumps({'head':head,'results':{'bindings':binds},'_class':q,'_type':t,'_fetched':'2026-11-11'},separators=(',',':')))
    print(key,len(qs),'items',len(binds),'rows',flush=True)
