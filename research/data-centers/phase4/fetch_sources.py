"""Bounded public research GETs. No credentials, uploads, jobs or production writes."""
import concurrent.futures,datetime,hashlib,json,urllib.request,urllib.parse
from pathlib import Path
P=Path(__file__).resolve().parent

def fetch(item):
 name,url=item
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.username or u.password:raise ValueError('Public HTTPS URL required')
 receipt={'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'InvestediaRobot/1.0','Accept':'text/html,application/json,application/pdf;q=0.9'})
  with urllib.request.urlopen(req,timeout=30) as r:
   raw=r.read(8*1024*1024+1)
   if len(raw)>8*1024*1024:raise ValueError('Body exceeds bounded research limit')
   receipt.update(status=r.status,final_url=r.url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   (P/'sources'/f'{name}.body').write_bytes(raw)
 except Exception as e:receipt.update(status=getattr(e,'code',None),failure=type(e).__name__)
 (P/'sources'/f'{name}.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return {'name':name,**receipt}
if __name__=='__main__':
 import sys
 jobs=json.loads(Path(sys.argv[1]).read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for row in pool.map(fetch,jobs.items()):print(json.dumps(row),flush=True)
