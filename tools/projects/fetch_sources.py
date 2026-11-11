"""Explicit download of already reviewed datasets. No discovery scraping or credentials.

First retain and manually review the dataset-specific terms and redistribution grant,
then add its hash-bound licence_review and exact official download URL to the manifest.
This command does not enable sources, rewrite the manifest or publish output.
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from tools.projects.build_projects import licence_gate

HOSTS={'wikidata':{'query.wikidata.org'},'gem':{'globalenergymonitor.org','globalenergymonitor.org.s3.amazonaws.com'},
       'world_bank':{'search.worldbank.org'},'eia':{'www.eia.gov'},'nga':{'msi.nga.mil'},
       'ourairports':{'ourairports.com'},'wri':{'datasets.wri.org'},'commons':{'commons.wikimedia.org'}}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirect requires explicit official-download review')


def fetch(manifest, budget=20*1024*1024):
    manifest=Path(manifest); spec=json.loads(manifest.read_text());directory=manifest.parent
    opener=urllib.request.build_opener(NoRedirect())
    total=0;result=[]
    for s in spec['sources']:
        if not s.get('enabled') or s.get('retained_snapshot'): continue
        licence_gate(s,directory)
        url=s.get('download_url','');u=urllib.parse.urlsplit(url)
        if u.scheme!='https' or u.hostname not in HOSTS[s['source']] or u.username or u.password or u.port not in (None,443):
            raise ValueError('Official HTTPS source URL required')
        if u.query and any(k.casefold() in ('token','key','apikey','api_key') for k,_ in urllib.parse.parse_qsl(u.query)):
            raise ValueError('No credentials in download URLs')
        dest=(directory/s['file']).resolve()
        if not dest.is_relative_to((directory/'raw').resolve()): raise ValueError('New downloads belong under ignored raw/')
        req=urllib.request.Request(url,headers={'User-Agent':'InvestediaRobot/1.0'})
        with opener.open(req,timeout=60) as response:
            body=response.read(budget-total+1)
        total+=len(body)
        if total>budget: raise ValueError('Raw download byte budget exceeded')
        # The expected dataset hash is approved out of band, not changed to match arbitrary downloads.
        import hashlib
        if hashlib.sha256(body).hexdigest()!=s['sha256']: raise ValueError('Download changed; review new version before ingestion')
        dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_suffix(dest.suffix+'.tmp');temp.write_bytes(body);temp.replace(dest)
        result.append({'source':s['source'],'bytes':len(body)});time.sleep(1)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,default=Path('data/projects/manifest.json'));a=p.parse_args()
    print(json.dumps(fetch(a.manifest)))
