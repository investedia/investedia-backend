"""Read-only local artifact consumer for backend integration tests and Claude's contract.
No server, shared code, deploy or external requests. Compact catalog first; details
are hash-checked lazy shards. An eventual provider can expose the same response shape.
"""
import copy,functools,hashlib,json,math,re
from pathlib import Path
class Catalog:
 def __init__(self,root):
  root=Path(root);pointer=json.loads((root/'current.json').read_text());version=pointer.get('version','')
  if not re.fullmatch('[a-f0-9]{64}',version):raise ValueError('Invalid artifact pointer')
  self.root=root;self.path=root/'versions'/version;self.manifest=json.loads((self.path/'manifest.json').read_text())
  if self.manifest['version']!=version:raise ValueError('Manifest version mismatch')
  raw=(self.path/'catalog.json').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=self.manifest['files']['catalog.json']:raise ValueError('Catalog checksum mismatch')
  self.doc=json.loads(raw);self.rows=self.doc['records'];self.byid={r['id']:r for r in self.rows};self.version=version
 @functools.lru_cache(maxsize=64)
 def _shard(self,shard):
  if not re.fullmatch('[a-f0-9]{2}',shard):raise ValueError('Invalid shard')
  name='details/'+shard+'.json';ref=self.manifest.get('detail_refs',{}).get(shard)
  if ref and not re.fullmatch('[a-f0-9]{64}',ref):raise ValueError('Invalid blob reference')
  data=((self.root/'blobs'/(ref+'.json')) if ref else self.path/name).read_bytes()
  if hashlib.sha256(data).hexdigest()!=self.manifest['files'][name]:raise ValueError('Detail checksum mismatch')
  return json.loads(data)
 def get(self,rid):
  if rid not in self.byid:return None
  return copy.deepcopy(self._shard(self.byid[rid]['shard'])[rid])
 def select(self,sector=None,status=None,company=None,q='',include_retired=False):
  if not isinstance(q,str) or len(q)>160:raise ValueError('Search must be at most 160 characters')
  q=q.casefold()
  return [r for r in self.rows if (include_retired or not r['retired']) and (not sector or r['sector']==sector) and (not status or r['status']==status) and (not company or r['company']==company or r['ticker']==company) and (not q or q in r['search'].casefold())]
 def query(self,*,sector=None,status=None,company=None,q='',offset=0,limit=50):
  if type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=200:raise ValueError('Invalid pagination; limit 1–200')
  rows=self.select(sector,status,company,q)
  return {'version':self.version,'synthetic':self.doc['synthetic'],'total':len(rows),'offset':offset,'limit':limit,'records':copy.deepcopy(rows[offset:offset+limit]),'production_approved':False}
 def clusters(self,*,cell_degrees=10,bbox=(-180,-90,180,90),**filters):
  if type(cell_degrees) not in (int,float) or not math.isfinite(cell_degrees) or not .25<=cell_degrees<=45:raise ValueError('Cell size must be 0.25–45 degrees')
  if len(bbox)!=4 or not all(type(x) in (int,float) and math.isfinite(x) for x in bbox):raise ValueError('Invalid bounds')
  west,south,east,north=bbox
  if not -180<=west<=180 or not -180<=east<=180 or not -90<=south<=north<=90:raise ValueError('Invalid geographic bounds')
  groups={};unknown=0
  for r in self.select(**filters):
   if r['precision']=='unknown':unknown+=1;continue
   lat,lon=r['lat'],r['lon']
   if not south<=lat<=north or not (west<=lon<=east if west<=east else lon>=west or lon<=east):continue
   key=(math.floor((lat+90)/cell_degrees),math.floor((lon+180)/cell_degrees));g=groups.setdefault(key,{'count':0,'lat_sum':0,'lon_sum':0,'approximate':0,'sample_ids':[]})
   g['count']+=1;g['lat_sum']+=lat;g['lon_sum']+=lon;g['approximate']+=r['precision']=='approximate'
   if len(g['sample_ids'])<5:g['sample_ids'].append(r['id'])
  return {'version':self.version,'synthetic':self.doc['synthetic'],'unknown_not_mapped':unknown,'clusters':[{'key':str(k[0])+':'+str(k[1]),'lat':v['lat_sum']/v['count'],'lon':v['lon_sum']/v['count'],'count':v['count'],'contains_approximate':bool(v['approximate']),'sample_ids':v['sample_ids']} for k,v in sorted(groups.items())]}
