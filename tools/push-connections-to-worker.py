"""Publish deterministic evidence-backed connections. --check is read-only."""
import argparse,importlib.util,json,os,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('news_push',ROOT/'tools/push-news-to-worker.py')
news=importlib.util.module_from_spec(spec);spec.loader.exec_module(news)
MAX_BYTES=2*1024*1024

def payload(path=None):
    data=json.loads(Path(path or ROOT/'assets/globe/connections.json').read_text(encoding='utf-8'))
    if data.get('schema')!='investedia.connections.v1' or not isinstance(data.get('connections'),list) or not data.get('generated_at'):raise ValueError('invalid connections')
    # Strip generator diagnostics; the Worker validates and whitelists each evidence record.
    return {k:data[k] for k in ('schema','generated_at','connections')}

def push(url,token,body):
    base=news.validate_url(url)
    if not token:raise ValueError('NEWS_INGEST_TOKEN required')
    encoded=json.dumps(body,ensure_ascii=False).encode('utf-8')
    if len(encoded)>MAX_BYTES:raise ValueError('connections upload exceeds bounded size; no partial snapshot sent')
    req=urllib.request.Request(base+'/v1/ingest/connections',data=encoded,method='POST',headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'User-Agent':'InvestediaRobot/1.0'})
    with urllib.request.build_opener(news.NoRedirect()).open(req,timeout=30) as response:result=json.loads(response.read(500_000))
    if not isinstance(result,dict) or result.get('ok') is not True:raise ValueError('connections ingest not acknowledged')
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--file',type=Path);a=p.parse_args(argv)
    try:
        body=payload(a.file)
        if a.check:print(json.dumps({'mode':'check-only','connections':len(body['connections']),'generated_at':body['generated_at']}));return 0
        r=push(os.environ.get('WORKER_URL','').strip(),os.environ.get('NEWS_INGEST_TOKEN','').strip(),body)
        print(json.dumps({'ok':True,'written':r.get('written'),'count':r.get('count'),'generated_at':r.get('generated_at')}));return 0
    except urllib.error.HTTPError as e:print('connections ingest failed: HTTP '+str(e.code),file=sys.stderr)
    except (ValueError,KeyError,TypeError,OSError):print('connections ingest failed: invalid settings, payload, response or unavailable network',file=sys.stderr)
    return 1
if __name__=='__main__':sys.exit(main())
