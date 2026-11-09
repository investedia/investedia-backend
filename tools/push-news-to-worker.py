"""Explicit news ingestion. Fail closed by default; --check never sends a request."""
import argparse,json,os,sys,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]

def payload(path=None,limit=40):
    with open(path or ROOT/'assets/globe/news-live.json',encoding='utf-8') as source:d=json.load(source)
    st=sorted(d.get('stories',[]),key=lambda s:s['published_at'],reverse=True)[:limit]
    if not st:raise ValueError('no articles to send')
    return {'generated_at':d.get('updated_at'),'stories':st}

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
        print(json.dumps({'ok':True,'written':result.get('written'),'count':result.get('count'),'reason':'unchanged' if result.get('reason')=='unchanged' else None}));return 0
    except urllib.error.HTTPError as e:print(f'worker ingest failed: HTTP {e.code}',file=sys.stderr)
    except (urllib.error.URLError,TimeoutError):print('worker ingest failed: network unavailable or timeout',file=sys.stderr)
    except (ValueError,KeyError,TypeError,OSError):print('worker ingest failed: invalid configuration, feed or response',file=sys.stderr)
    return 1
if __name__=='__main__':sys.exit(main())
