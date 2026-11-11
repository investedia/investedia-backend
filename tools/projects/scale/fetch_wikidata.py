"""Resumable energy fetch. Stops at source budgets/cooldowns and keeps completed batches.
No workflow dispatch, credentials, publication, financial jobs or generated facts.
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.projects.scale.transport import Client,Deferred,BudgetExceeded
from tools.projects.scale.queries import ids as id_query, details


def run(root=ROOT,seconds=420,max_items=1500,batch_size=80,refresh=False,only=None,cached_ids=False):
    root=Path(root);config=json.loads((root/'data/projects/scale/classes.json').read_text())
    client=Client(root/'data/projects/raw/scale/http',seconds=seconds)
    base=json.loads((root/'data/projects/manifest.json').read_text())
    review=next(s['licence_review'] for s in base['sources'] if s.get('licence_review') and s['source']=='wikidata')
    original_path=root/'data/projects/scale-manifest.json'
    previous=json.loads(original_path.read_text()) if original_path.exists() else {'sources':[]}
    sources={s['class_key']:s for s in previous['sources']};reports=[];deferred=False
    for cls in config['classes']:
        if only and cls['key'] not in only:continue
        selected=[];bindings=[];receipts=[];covered_ids=set();complete=False;reason=None;pending=[];failed_ids=[]
        try:
            old_spec=next((s for s in base['sources'] if s.get('file')=='cache/wikidata-'+cls['key']+'.json'),None)
            if cached_ids and old_spec:
                old_path=root/'data/projects'/old_spec['file']
                if hashlib.sha256(old_path.read_bytes()).hexdigest()!=old_spec['sha256']:raise ValueError('P19 list hash mismatch')
                old_rows=json.loads(old_path.read_text())['results']['bindings']
                priority={}
                for row in old_rows:
                    key=row['item']['value'].rsplit('/',1)[-1]
                    status=row.get('statusLabel',{}).get('value','')
                    year=row.get('entry',{}).get('value','')[:4]
                    score=3 if status in ('building or structure under construction','proposed building or structure','pre-construction') else 2 if year.isdigit() and int(year)>=2020 else 0
                    priority[key]=max(priority.get(key,0),score)
                selected=sorted(priority,key=lambda key:(-priority[key],key))[:max_items]
                reason='ID list reused from the reviewed P19 cache; fresh detail pass, not a fresh exhaustive class census'
            else:
                for offset in range(0,max_items,500):
                    size=min(500,max_items-offset);payload,receipt=client.sparql(id_query(cls['qid'],offset,size,current_only=True),refresh)
                    rows=payload['results']['bindings'];selected.extend(r['item']['value'].rsplit('/',1)[-1] for r in rows)
                    if len(rows)<size:complete=True;break
                    time.sleep(1.1)
            selected=list(dict.fromkeys(selected));pending=[selected[i:i+batch_size] for i in range(0,len(selected),batch_size)]
            print(f"{cls['key']}: {len(selected)} ids; list complete={complete}",flush=True)
            while pending:
                batch=pending[0]
                try:payload,receipt=client.sparql(details(batch),refresh)
                except TimeoutError:
                    if len(batch)>5:
                        n=len(batch)//2;pending[:1]=[batch[:n],batch[n:]]
                        print(f"{cls['key']}: timed out; reducing {len(batch)}-item batch",flush=True)
                    else:
                        failed_ids.extend(batch);pending.pop(0)
                        print(f"{cls['key']}: queued {len(batch)} slow ids; continuing other batches",flush=True)
                    continue
                rows=payload['results']['bindings']
                if len(rows)>=20000:
                    if len(batch)==1:raise ValueError('Single-entity detail truncation; review required')
                    n=len(batch)//2;pending[:1]=[batch[:n],batch[n:]];continue
                expected=set(batch)
                if any(r['item']['value'].rsplit('/',1)[-1] not in expected for r in rows):raise ValueError('Unexpected source entity')
                bindings.extend({**r,'__checked_at':{'value':receipt['checked_at'][:10]}} for r in rows)
                receipts.append({'query_sha256':hashlib.sha256(details(batch).encode()).hexdigest(),'checked_at':receipt['checked_at'],'sha256':receipt['sha256'],'requested_ids':batch,'requested':len(batch),'returned':len({r['item']['value'] for r in rows})})
                covered_ids.update(batch)
                pending.pop(0);print(f"{cls['key']}: {len(receipts)} batches complete; {sum(map(len,pending))} ids pending",flush=True)
                time.sleep(1.1)
        except (Deferred,BudgetExceeded,TimeoutError,OSError,ValueError) as error:
            reason=str(error) if isinstance(error,(Deferred,BudgetExceeded,ValueError)) else type(error).__name__
            deferred=isinstance(error,(Deferred,BudgetExceeded))
            print(f"{cls['key']}: queued: {reason}",flush=True)
        if receipts:
            previous_pack=None
            if cls['key'] in sources:
                old_path=root/'data/projects'/sources[cls['key']]['file']
                if old_path.is_file() and hashlib.sha256(old_path.read_bytes()).hexdigest()==sources[cls['key']]['sha256']:
                    previous_pack=json.loads(old_path.read_text())
                    bindings=[r for r in previous_pack['results']['bindings'] if r['item']['value'].rsplit('/',1)[-1] not in covered_ids]+bindings
            pack={'schema':'investedia.projects.wikidata-scale-cache.v1','class':cls,'results':{'bindings':bindings},
                  'receipts':(previous_pack or {}).get('receipts',[])+receipts,'listed_ids':len(selected),'list_complete':complete,'list_scope':'direct class; current-candidate filter, not an all-subclass census','pending_ids':sum(map(len,pending))+len(failed_ids),'slow_ids':failed_ids,'reason':reason}
            path=root/f"data/projects/cache/scale-{cls['key']}.json";path.write_text(json.dumps(pack,ensure_ascii=False,separators=(',',':'))+'\n')
            checked=min(r['checked_at'][:10] for r in receipts)
            sources[cls['key']]={'source':'wikidata','name':f"Wikidata (CC0), current {cls['label']}",'class_key':cls['key'],
                'enabled':True,'scale_v1':True,'type':cls['type'],'record_level':'site','file':str(path.relative_to(root/'data/projects')),
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'licence':'CC0 1.0','checked_at':checked,
                'url':'https://query.wikidata.org/sparql','licence_review':review}
        reports.append({'class':cls['key'],'listed_ids':len(selected),'list_complete':complete,'completed_batches':len(receipts),
                        'pending_ids':sum(map(len,pending))+len(failed_ids),'slow_ids':failed_ids,'reason':reason,'cached_source_retained':not receipts and cls['key'] in sources})
        if deferred:break
    manifest={'schema':'investedia.projects.raw-manifest.v1','build_date':dt.datetime.now(dt.timezone.utc).date().isoformat(),
              'policy':{'name':'projects-scale-current-v1','completed_since':2020,'max_coordinate_precision_degrees':0.001},
              'sources':list(sources.values())}
    # Existing completed sources remain available across retries; never replace with a failure/empty body.
    original_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report={'schema':'investedia.projects.scale-fetch.v1','requests':client.requests,'cache_hits':client.hits,'bytes':client.bytes,
            'sources':reports,'unvisited_classes':[c['key'] for c in config['classes'] if c['key'] not in {r['class'] for r in reports}],'queued':config.get('queued',{}),'budget_seconds':seconds,'max_items_per_class':max_items,
            'no_publication':True,'gemini_calls':0}
    history_path=root/'data/projects/scale/fetch-runs.json'
    history=json.loads(history_path.read_text()) if history_path.exists() else []
    history.append(report);history_path.write_text(json.dumps(history,indent=2)+'\n')
    (root/'data/projects/scale/fetch-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=int,default=420);p.add_argument('--max-items',type=int,default=1500)
    p.add_argument('--batch-size',type=int,default=80);p.add_argument('--refresh',action='store_true');p.add_argument('--cached-ids',action='store_true');p.add_argument('--classes',nargs='+')
    a=p.parse_args()
    if not 1<=a.batch_size<=80 or not 1<=a.max_items<=10000 or not 1<=a.seconds<=1800:p.error('Invalid source budget')
    print(json.dumps(run(seconds=a.seconds,max_items=a.max_items,batch_size=a.batch_size,refresh=a.refresh,only=a.classes,cached_ids=a.cached_ids),indent=2))
