"""Explicit news ingestion. Fail closed by default; --check never sends a request."""
import argparse,json,os,sys,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]

def site_stats(root=ROOT):
    """Homepage totals: every article in the robot's day files (assets/globe/events), the distinct news sources behind them,
    and the projects on the globe. Missing inputs are left out, never guessed."""
    ids,sources=set(),set()
    for f in sorted((root/'assets/globe/events').glob('*.json')):
        try:d=json.loads(f.read_text(encoding='utf-8'))
        except Exception:continue
        for e in d.get('events',[]):
            if e.get('id'):ids.add(e['id'])
            if e.get('src'):sources.add(str(e['src']).strip().lower())
    out={}
    if ids:out['articles']=len(ids);out['sources']=len(sources)
    try:out['projects']=len(json.loads((root/'assets/globe/projects.json').read_text(encoding='utf-8'))['projects'])
    except Exception:pass
    return out

def library_days(root=ROOT,n=2):
    """The robot's last n day files as compact rows for the website's article library (photo joined from the live feed when known)."""
    imgs={}
    try:
        for s in json.loads((root/'assets/globe/news-live.json').read_text(encoding='utf-8')).get('stories',[]):
            if (s.get('image') or {}).get('file'):imgs[s['id']]=s['image']['file']
    except Exception:pass
    out={}
    for f in sorted((root/'assets/globe/events').glob('*.json'))[-n:]:
        try:d=json.loads(f.read_text(encoding='utf-8'))
        except Exception:continue
        rows=[]
        for e in d.get('events',[]):
            if not e.get('id') or not e.get('title') or not e.get('at'):continue
            loc=e.get('loc') or {}
            r={'id':e['id'],'h':e['title'],'c':e.get('cat') or 'news','t':e['at'],'s':e.get('src'),'n':loc.get('country'),'g':loc.get('region'),'k':e.get('n_src') or 1}
            if e['id'] in imgs:r['i']=imgs[e['id']]
            rows.append(r)
        if rows:out[f.stem]=rows
    return out

def push_library(url,token,days,timeout=30):
    req=urllib.request.Request(url+'/v1/ingest/library',data=json.dumps({'days':days},ensure_ascii=False).encode('utf-8'),method='POST',headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'User-Agent':'InvestediaRobot/1.0'})
    with urllib.request.build_opener(NoRedirect).open(req,timeout=timeout) as response:return json.loads(response.read(100_000))

def payload(path=None,limit=None):
    limit=limit or min(80,int(os.environ.get('PUSH_LIMIT') or 40))
    with open(path or ROOT/'assets/globe/news-live.json',encoding='utf-8') as source:d=json.load(source)
    st=sorted(d.get('stories',[]),key=lambda s:s['published_at'],reverse=True)[:limit]
    if not st:raise ValueError('no articles to send')
    return {'generated_at':d.get('updated_at'),'stories':st,'stats':site_stats()}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise urllib.error.HTTPError(req.full_url,code,'redirect refused',headers,fp)

def validate_url(url):
    u=urlsplit(url)
    if u.username or u.password or u.query or u.fragment or not u.hostname:raise ValueError('Worker URL must not contain credentials, query parameters or fragments')
    if u.scheme!='https' and not (u.scheme=='http' and u.hostname in {'127.0.0.1','localhost','::1'}):raise ValueError('Use HTTPS, or HTTP loopback for local tests')
    return url.rstrip('/')

def push(url,token,body,timeout=20):
    url=validate_url(url)
    if not token:raise ValueError('NEWS_INGEST_TOKEN is required')
    req=urllib.request.Request(url+'/v1/ingest/news',data=json.dumps(body,ensure_ascii=False).encode('utf-8'),method='POST',headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'User-Agent':'InvestediaRobot/1.0'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
        result=json.loads(response.read(500_000))
    if not isinstance(result,dict) or result.get('ok') is not True:raise ValueError('Worker did not acknowledge ingestion')
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--file',type=Path);p.add_argument('--check',action='store_true');p.add_argument('--optional',action='store_true',help='Allow absent configuration; actual upload failures still fail');args=p.parse_args(argv)
    try:
        body=payload(args.file)
        if args.check:
            print(json.dumps({'mode':'check-only','articles':len(body['stories']),'generated_at':body['generated_at']}));return 0
        url=os.environ.get('WORKER_URL','').strip();token=os.environ.get('NEWS_INGEST_TOKEN','').strip()
        if not url or not token:
            if args.optional:print('worker ingest unconfigured: explicitly skipped');return 0
            print('worker ingest unconfigured: WORKER_URL and NEWS_INGEST_TOKEN are required',file=sys.stderr);return 2
        result=push(url,token,body)
        print(json.dumps({'ok':True,'written':result.get('written'),'count':result.get('count'),'reason':'unchanged' if result.get('reason')=='unchanged' else None}))
        # Article library sync is best effort: a failure here never fails the news run.
        try:
            days=library_days()
            if days:print(json.dumps({'library':push_library(validate_url(url),token,days).get('written'),'days':sorted(days)}))
        except Exception as e:print('library sync skipped: '+type(e).__name__,file=sys.stderr)
        return 0
    except urllib.error.HTTPError as e:
        try:detail=e.read(400).decode('utf-8','replace')
        except Exception:detail=''
        print(f'worker ingest failed: HTTP {e.code} {detail}',file=sys.stderr)
    except (urllib.error.URLError,TimeoutError):print('worker ingest failed: network unavailable or timeout',file=sys.stderr)
    except (ValueError,KeyError,TypeError,OSError):print('worker ingest failed: invalid configuration, feed or response',file=sys.stderr)
    return 1
if __name__=='__main__':sys.exit(main())
