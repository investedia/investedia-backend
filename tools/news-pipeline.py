"""Bounded priority-news job. Default preflight is read-only; --run explicitly generates and ingests."""
import argparse,contextlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]

def preflight(require_secrets=False):
    required=['update_globe_news.py','news_core.py','registry.py','events.py','tools/globe-news/iso.json','tools/globe-news/wb-countries.json','tools/globe-news/connections.py','tools/push-connections-to-worker.py','assets/globe/countries-50m.json','assets/globe/news-live.json','assets/quotes.js']
    missing=[x for x in required if not (ROOT/x).is_file()]
    secrets=[x for x in ['GEMINI_API_KEY','WORKER_URL','NEWS_INGEST_TOKEN'] if not os.environ.get(x,'').strip()]
    if missing:raise ValueError('missing pipeline files: '+', '.join(missing))
    if require_secrets and secrets:raise ValueError('missing required settings: '+', '.join(secrets))
    return {'required_files':'present','missing_settings':secrets,'scheduled_jobs_started':False}

def verify_generation(status,started,tier_name='priority'):
    if not isinstance(status,dict):raise ValueError('invalid generator status')
    tier=status.get('tiers',{}).get(tier_name,{})
    last=datetime.fromisoformat(tier.get('last_success','').replace('Z','+00:00')).timestamp()
    if last < started-2:raise ValueError('generator did not record a successful '+tier_name+' run')
    if not status.get('fetched'):raise ValueError('no articles fetched; retaining prior feed')
    if status.get('candidates') and not status.get('gemini_ok'):raise ValueError('article selection failed; retaining prior feed')
    if not status.get('stories_online'):raise ValueError('no usable articles; retaining prior feed')

@contextlib.contextmanager
def exclusive_run():
    folder=ROOT/'.local';folder.mkdir(exist_ok=True);lock=folder/'news-pipeline.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(descriptor,'w') as f:f.write(str(os.getpid()))
        yield
    finally:lock.unlink(missing_ok=True)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--tier',choices=['priority','broad'],default='priority');p.add_argument('--frontend',type=Path,help='Explicitly export saved files to a frontend after successful ingest');args=p.parse_args(argv)
    try:
        result=preflight(args.run)
        if not args.run:print(json.dumps({'mode':'preflight-only',**result}));return 0
        if args.frontend and not (args.frontend.resolve()/'scripts/sync-snapshots.py').is_file():raise ValueError('invalid frontend checkout')
        # No V5/financial engine dispatch, no broad-history rebuild and no Git operations.
        with exclusive_run():
            started=time.time();env={**os.environ,'NEWS_TIER':args.tier,'PYTHONUTF8':'1','PUSH_LIMIT':'80' if args.tier=='broad' else '40'}
            env.pop('BACKFILL_DAYS',None)
            log=ROOT/'.local/news-generation.log'
            with log.open('w',encoding='utf-8') as output:
                subprocess.run([sys.executable,'-X','utf8',str(ROOT/'update_globe_news.py'),'--tier',args.tier],cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=420 if args.tier=='priority' else 1200)
            status=json.loads((ROOT/'assets/globe/news-status.json').read_text(encoding='utf-8'))
            verify_generation(status,started,args.tier)
            with log.open('a',encoding='utf-8') as output:
                subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/globe-news/connections.py')],cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=90)
            subprocess.run([sys.executable,str(ROOT/'tools/push-news-to-worker.py')],cwd=ROOT,env=env,check=True,timeout=45)
            subprocess.run([sys.executable,str(ROOT/'tools/push-connections-to-worker.py')],cwd=ROOT,env=env,check=True,timeout=45)
            if args.frontend:
                frontend=args.frontend.resolve();sync=frontend/'scripts/sync-snapshots.py'
                if not sync.is_file():raise ValueError('choose a frontend checkout containing scripts/sync-snapshots.py')
                subprocess.run([sys.executable,str(sync),'--backend',str(ROOT)],cwd=frontend,env=env,check=True,timeout=120)
                subprocess.run([sys.executable,'-X','utf8',str(frontend/'build.py')],cwd=frontend,env=env,check=True,timeout=120)
            print(json.dumps({'ok':True,'tier':args.tier,'ingestion':'acknowledged','frontend_exported':bool(args.frontend)}));return 0
    except FileExistsError:print('news pipeline already locked; check the existing process before removing a stale lock',file=sys.stderr)
    except (ValueError,OSError,KeyError):print('news pipeline failed: preflight, generator status or export configuration is invalid; inspect .local logs and required settings',file=sys.stderr)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired):print('news pipeline failed: generation, ingestion or export did not complete; no success reported',file=sys.stderr)
    return 1
if __name__=='__main__':sys.exit(main())
