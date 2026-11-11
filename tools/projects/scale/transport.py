"""Anonymous, bounded HTTP cache with conditional requests and persistent cooldowns."""
import datetime as dt
import email.utils
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA='InvestediaRobot/1.0'
class Deferred(RuntimeError): pass
class BudgetExceeded(RuntimeError): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ValueError('Redirect needs source review')


class Client:
    def __init__(self, directory, seconds=420, max_bytes=32*1024*1024, hosts=('query.wikidata.org',)):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.deadline=time.monotonic()+seconds;self.max_bytes=max_bytes;self.hosts=set(hosts)
        self.bytes=0;self.requests=0;self.hits=0;self.opener=urllib.request.build_opener(NoRedirect())
        self.cooldown=self.directory/'cooldowns.json'

    def get(self,url,refresh=False):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in self.hosts or parsed.username or parsed.password:
            raise ValueError('Unreviewed source URL')
        key=hashlib.sha256(url.encode()).hexdigest();body_path=self.directory/(key+'.body');receipt_path=self.directory/(key+'.json')
        receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        if receipt and (not body_path.is_file() or hashlib.sha256(body_path.read_bytes()).hexdigest()!=receipt['sha256']):
            raise ValueError('Raw cache integrity failure')
        if receipt and receipt.get('url')!=url:raise ValueError('Raw receipt URL mismatch')
        fresh=bool(receipt and (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(receipt['checked_at'])).total_seconds()<86400)
        if receipt and not refresh and fresh:
            self.hits+=1;return body_path.read_bytes(),receipt
        if time.monotonic()>=self.deadline:raise BudgetExceeded('Source time budget reached')
        cooldowns=json.loads(self.cooldown.read_text()) if self.cooldown.exists() else {}
        until=cooldowns.get(parsed.hostname,0)
        if time.time()<until:raise Deferred('Source cooldown until '+dt.datetime.fromtimestamp(until,dt.timezone.utc).isoformat())
        headers={'User-Agent':UA,'Accept':'application/sparql-results+json, application/json'}
        if receipt:
            if receipt.get('etag'):headers['If-None-Match']=receipt['etag']
            if receipt.get('last_modified'):headers['If-Modified-Since']=receipt['last_modified']
        request=urllib.request.Request(url,headers=headers)
        for attempt in range(2):
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise BudgetExceeded('Source time budget reached')
            try:
                self.requests+=1
                with self.opener.open(request,timeout=min(40,remaining)) as response:
                    data=response.read(self.max_bytes-self.bytes+1);response_headers=response.headers
                self.bytes+=len(data)
                if self.bytes>self.max_bytes:raise BudgetExceeded('Source byte budget reached')
                checked=dt.datetime.now(dt.timezone.utc).isoformat()
                receipt={'url':url,'retrieved_at':checked,'checked_at':checked,'sha256':hashlib.sha256(data).hexdigest(),
                         'etag':response_headers.get('ETag'),'last_modified':response_headers.get('Last-Modified')}
                temp=body_path.with_suffix('.tmp');temp.write_bytes(data);temp.replace(body_path)
                receipt_path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
                return data,receipt
            except urllib.error.HTTPError as error:
                if error.code==304 and receipt:
                    receipt['checked_at']=dt.datetime.now(dt.timezone.utc).isoformat()
                    receipt_path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
                    return body_path.read_bytes(),receipt
                if error.code in (429,503):
                    retry=error.headers.get('Retry-After','120')
                    try:delay=int(retry)
                    except ValueError:
                        delay=max(0,email.utils.parsedate_to_datetime(retry).timestamp()-time.time())
                    cooldowns[parsed.hostname]=time.time()+max(1,delay)
                    self.cooldown.write_text(json.dumps(cooldowns,sort_keys=True)+'\n')
                    raise Deferred(f'HTTP {error.code}; source requests a {round(delay)} second cooldown') from error
                if error.code in (502,504) and attempt==0 and remaining>3:
                    time.sleep(2);continue
                raise

    def sparql(self,query,refresh=False):
        url='https://query.wikidata.org/sparql?'+urllib.parse.urlencode({'query':query,'format':'json'})
        body,receipt=self.get(url,refresh)
        payload=json.loads(body)
        if not isinstance(payload.get('results',{}).get('bindings'),list):raise ValueError('Unexpected SPARQL response')
        return payload,receipt
