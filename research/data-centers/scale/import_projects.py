"""Deterministic research-local batch imports. Never publishes or edits production.
CLI accepts a JSON bundle or header + JSONL records; writes content-addressed local
versions, atomically selecting a version only when the entire batch passes.
"""
import argparse,copy,hashlib,json,os,re,sys,tempfile,time,fcntl,datetime
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'phase4'))
from sector_adapter import validate,validate_bundle,digest,public_projection,evidence_valid
SCHEMA='investedia.projects.import.v1';MAX_RECORDS=100000;MAX_BYTES=64*1024*1024
SECRET_KEYS=re.compile(r'(^|_)(password|token|secret|api_key|service_role|private_key)($|_)',re.I)
class ImportFailure(Exception):
 def __init__(self,errors):self.errors=errors;super().__init__('Batch rejected; previous version retained')
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def credential_keys(x):
 if isinstance(x,dict):return any(SECRET_KEYS.search(str(k)) or credential_keys(v) for k,v in x.items())
 if isinstance(x,list):return any(credential_keys(v) for v in x)
 return False

def malformed_evidence(value,synthetic):
 if isinstance(value,dict):
  if {'url','sha256','checked_at','locator'}.issubset(value):
   try:datetime.date.fromisoformat(value['checked_at'][:10])
   except (ValueError,TypeError):return True
   if not synthetic and value['sha256']=='0'*64:return True
  return any(malformed_evidence(x,synthetic) for x in value.values())
 if isinstance(value,list):return any(malformed_evidence(x,synthetic) for x in value)
 return False

def read_input(path):
 path=Path(path)
 if path.stat().st_size>MAX_BYTES:raise ImportFailure([{'row':0,'code':'input_too_large','field':'input'}])
 if path.suffix=='.jsonl':
  with path.open() as f:
   first=json.loads(next(f));header=first['header'];records=[]
   for n,line in enumerate(f,1):
    if n>MAX_RECORDS:raise ImportFailure([{'row':n,'code':'record_cap','field':'records'}])
    if line.strip():records.append(json.loads(line))
  return {**header,'records':records}
 return json.loads(path.read_text())

def identity(r):
 s=r.get('source_identity',{})
 return (r['sector'],s.get('authority'),s.get('id'))

def validate_import(r,synthetic,row):
 errors=[]
 def err(code,field):errors.append({'row':row,'code':code,'field':field})
 if credential_keys(r):err('credential_field_forbidden','record');return errors
 if not isinstance(r,dict):err('record_not_object','record');return errors
 if r.get('sector')=='energy':err('energy_read_only','sector');return errors
 origin=r.get('source_identity')
 if not isinstance(origin,dict) or any(not isinstance(origin.get(k),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,199}',origin[k]) for k in ('authority','id')):err('source_identity_required','source_identity')
 if not isinstance(r.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,199}',r['id']):err('stable_id_required','id')
 for key in ('asset','status','location','identity_evidence','verification','reuse'):
  if not isinstance(r.get(key),dict):err('object_required',key)
 for key in ('exposures','imagery'):
  if not isinstance(r.get(key),list):err('array_required',key)
 if errors:return errors
 if r['verification'].get('classification') not in {'company_confirmed','regulator_confirmed','mixed_company_and_regulator','research_only_affiliation','unverified','conflicted','synthetic'}:err('verification_state_invalid','verification.classification')
 if malformed_evidence(r,synthetic):err('evidence_date_or_hash_invalid','evidence')
 if r.get('synthetic') is not synthetic:err('synthetic_boundary_mismatch','synthetic')
 if synthetic and (not str(r.get('id','')).startswith('test:') or r.get('verification',{}).get('classification')!='synthetic' or not r.get('preview_only')):err('test_record_not_isolated','verification')
 if not synthetic and (str(r.get('id','')).startswith('test:') or origin.get('authority')=='synthetic_fixture' or r.get('verification',{}).get('classification')=='synthetic'):err('test_id_in_real_import','id')
 try:validate(r)
 except (ValueError,KeyError,TypeError,AttributeError):err('contract_invalid','record')
 # Prevent an omitted image licence from becoming a browser request.
 if any(not isinstance(im,dict) or not isinstance(im.get('url'),str) or not im['url'].startswith('https://') for im in r.get('imagery',[])):err('image_url_invalid','imagery')
 return errors

def resolve_companies(rows,companies,refresh=False):
 errors=[]
 for ref,c in companies.items():
  ident=c.get('identity',{}) if isinstance(c,dict) else {}
  if not isinstance(ident,dict):ident={}
  patterns={'lei':r'[A-Z0-9]{20}','cik':r'[0-9]{10}','qid':r'Q[1-9][0-9]*','registry':r'[A-Za-z0-9]+:[A-Za-z0-9:_.-]+'}
  if ident.get('scheme') not in patterns or not isinstance(ident.get('value'),str) or not re.fullmatch(patterns[ident['scheme']],ident['value']) or ref!=ident.get('scheme','')+':'+str(ident.get('value','')) or not evidence_valid(ident.get('evidence')):
   errors.append({'row':0,'code':'company_identifier_evidence_required','field':'companies'})
 if errors:raise ImportFailure(errors)
 out=[]
 for i,original in enumerate(rows,1):
  r=copy.deepcopy(original)
  if not isinstance(r,dict):out.append(r);continue
  for e in r.get('exposures',[]) if isinstance(r.get('exposures'),list) else []:
   if not isinstance(e,dict) or not e.get('company_ref'):continue
   ref=e['company_ref']
   if not isinstance(ref,str) or ref not in companies:errors.append({'row':i,'code':'unknown_company_reference','field':'exposures.company_ref'});continue
   c=companies[ref]
   if not refresh and any(e.get(k) is not None and e.get(k)!=c.get(k) for k in ('listing','headquarters')):
    errors.append({'row':i,'code':'company_reference_conflict','field':'exposures.company_ref'});continue
   e['listing']=copy.deepcopy(c.get('listing'));e['headquarters']=copy.deepcopy(c.get('headquarters'));e['company_identity']=copy.deepcopy(c['identity'])
  out.append(r)
 if errors:raise ImportFailure(errors)
 return out

def assemble(bundle,base=None):
 if not isinstance(bundle,dict) or bundle.get('schema')!=SCHEMA or type(bundle.get('synthetic')) is not bool:raise ImportFailure([{'row':0,'code':'invalid_header','field':'schema/synthetic'}])
 if credential_keys(bundle):raise ImportFailure([{'row':0,'code':'credential_field_forbidden','field':'input'}])
 incoming=bundle.get('records');synthetic=bundle['synthetic']
 if not isinstance(incoming,list) or len(incoming)>MAX_RECORDS:raise ImportFailure([{'row':0,'code':'record_cap_or_type','field':'records'}])
 old=copy.deepcopy(base or {'records':[],'synthetic':synthetic})
 if old.get('synthetic') is not synthetic:raise ImportFailure([{'row':0,'code':'cannot_mix_real_and_synthetic','field':'synthetic'}])
 companies=copy.deepcopy(old.get('companies',{}))
 supplied=bundle.get('companies',{})
 if not isinstance(supplied,dict) or credential_keys(supplied):raise ImportFailure([{'row':0,'code':'invalid_company_registry','field':'companies'}])
 companies.update(supplied)
 incoming=resolve_companies(incoming,companies)
 prior=resolve_companies(old.get('records',[]),companies,refresh=True)
 stored={r['id']:r for r in prior};seen={};origin={identity(r):r['id'] for r in stored.values()};errors=[];counts={'input':len(incoming),'inserted':0,'updated':0,'unchanged':0,'duplicates':0,'retired':0,'company_refreshed':sum(digest(a)!=digest(b) for a,b in zip(old.get('records',[]),prior))}
 for i,r in enumerate(incoming,1):
  issues=validate_import(r,synthetic,i)
  if issues:errors+=issues;continue
  rid=r['id'];key=identity(r)
  if rid in seen:
   if digest(seen[rid])==digest(r):counts['duplicates']+=1
   else:errors.append({'row':i,'code':'conflicting_duplicate_id','field':'id'})
   continue
  seen[rid]=r
  if key in origin and origin[key]!=rid:errors.append({'row':i,'code':'source_identity_collision','field':'source_identity'});continue
  if rid in stored:
   if identity(stored[rid])!=key:errors.append({'row':i,'code':'identity_changed','field':'source_identity'});continue
   counts['unchanged' if digest(stored[rid])==digest(r) else 'updated']+=1
  else:counts['inserted']+=1
  origin[key]=rid;stored[rid]=copy.deepcopy(r)
 retire=bundle.get('retire',[])
 if not isinstance(retire,list):raise ImportFailure([{'row':0,'code':'array_required','field':'retire'}])
 for i,t in enumerate(retire,1):
  if not isinstance(t,dict) or not t.get('reason') or not t.get('as_of') or t.get('id') not in stored or digest(stored[t['id']])!=t.get('expected_sha256'):
   errors.append({'row':i,'code':'retirement_requires_matching_hash_and_reason','field':'retire'});continue
  r=stored[t['id']];r['lifecycle']={'retired':True,'reason':t['reason'],'as_of':t['as_of']};counts['retired']+=1
 if len(stored)>MAX_RECORDS:errors.append({'row':0,'code':'total_record_cap','field':'records'})
 if errors:raise ImportFailure(errors)
 rows=sorted(stored.values(),key=lambda r:r['id'])
 for i,r in enumerate(rows,1):
  issues=validate_import(r,synthetic,i)
  if issues:raise ImportFailure(issues)
 try:validate_bundle(rows)
 except (ValueError,KeyError,TypeError):raise ImportFailure([{'row':0,'code':'invalid_hierarchy_or_bundle','field':'asset.parent_id'}])
 state={'schema':'investedia.projects.local-state.v1','synthetic':synthetic,'records':rows}
 if companies:state['companies']=companies
 return state,counts

def check_output(root):
 root=Path(root).resolve();allowed=(P/'builds').resolve()
 if not (root.is_relative_to(allowed) or root.is_relative_to(Path('/tmp'))):raise ValueError('Output restricted to scale/builds or /tmp; no production paths')
 root.mkdir(parents=True,exist_ok=True);return root

def store_blob(root,data):
 sha=hashlib.sha256(data).hexdigest();folder=root/'blobs';folder.mkdir(exist_ok=True);path=folder/(sha+'.json')
 if path.exists():
  if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Existing immutable blob checksum mismatch')
  return sha,path
 fd,name=tempfile.mkstemp(prefix='.blob-',dir=folder)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  try:os.link(name,path)
  except FileExistsError:
   if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Blob collision/corruption')
 finally:os.unlink(name)
 return sha,path

def materialize(state,counts,output):
 root=check_output(output);blob=canonical(state);version=hashlib.sha256(blob).hexdigest();dest=root/'versions'/version
 if not dest.exists():
  temp=Path(tempfile.mkdtemp(prefix='.stage-',dir=root))
  try:
   (temp/'details').mkdir();shards={};catalog=[]
   for r in state['records']:
    shard=hashlib.sha256(r['id'].encode()).hexdigest()[:2];shards.setdefault(shard,{})[r['id']]=r
    ex=r.get('exposures',[]);listing=next((e.get('listing') for e in ex if e.get('listing')),None)
    catalog.append({'id':r['id'],'name':r['name'],'sector':r['sector'],'status':r['status']['stage'],'status_label':r['status']['label'],'asset':r['asset']['category'],'country':r.get('country_code'),'city':r.get('city'),'lat':r['location']['lat'],'lon':r['location']['lon'],'precision':r['location']['precision'],'company':listing.get('name') if listing else r['verification'].get('company'),'ticker':listing.get('ticker') if listing else None,'verification':r['verification']['classification'],'synthetic':state['synthetic'],'production_approved':False,'retired':bool(r.get('lifecycle',{}).get('retired')),'shard':shard,'search':' '.join(str(x or '') for x in [r['name'],r.get('city'),r.get('country_code'),listing.get('name') if listing else r['verification'].get('company'),listing.get('ticker') if listing else None]).lower()})
   (temp/'state.json').write_bytes(blob)
   (temp/'catalog.json').write_bytes(canonical({'schema':'investedia.projects.catalog.v1','version':version,'synthetic':state['synthetic'],'records':catalog}))
   files={};detail_refs={}
   for shard,items in sorted(shards.items()):
    data=canonical(items);name=f'details/{shard}.json';sha,blob_path=store_blob(root,data);os.link(blob_path,temp/name);files[name]=sha;detail_refs[shard]=sha
   files['state.json']=hashlib.sha256(blob).hexdigest();files['catalog.json']=hashlib.sha256((temp/'catalog.json').read_bytes()).hexdigest()
   manifest={'schema':'investedia.projects.local-artifact.v1','version':version,'synthetic':state['synthetic'],'records':len(catalog),'files':files,'production_approved':False,'publication_tool':False,'detail_refs':detail_refs,'blob_root':'../../blobs/'}
   (temp/'manifest.json').write_bytes(canonical(manifest));dest.parent.mkdir(exist_ok=True);os.rename(temp,dest)
  except BaseException:
   import shutil;shutil.rmtree(temp,ignore_errors=True);raise
 # An existing immutable version must still verify before selecting it again.
 manifest=json.loads((dest/'manifest.json').read_text())
 for name,sha in manifest['files'].items():
  if name not in {'state.json','catalog.json'} and not re.fullmatch(r'details/[a-f0-9]{2}\.json',name):raise ValueError('Invalid manifest path')
  if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:raise ValueError('Existing version checksum mismatch')
 pointer={'version':version,'path':'versions/'+version,'synthetic':state['synthetic'],'production_approved':False}
 fd,name=tempfile.mkstemp(prefix='.pointer-',dir=root)
 with os.fdopen(fd,'wb') as f:f.write(canonical(pointer));f.flush();os.fsync(f.fileno())
 os.replace(name,root/'current.json')
 return {'version':version,'records':len(state['records']),**counts}

def run(input_path,output,incremental=False):
 root=check_output(output)
 # Serialize read-modify-select operations; concurrent incremental writers must not lose updates.
 with (root/'.import.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ImportFailure([{'row':0,'code':'import_already_running','field':'output'}])
  try:
   bundle=read_input(input_path);base=None
   if incremental and (root/'current.json').exists():
    pointer=json.loads((root/'current.json').read_text());version=pointer.get('version','')
    if not re.fullmatch('[a-f0-9]{64}',version):raise ValueError('Invalid local version pointer')
    content=(root/'versions'/version/'state.json').read_bytes()
    if hashlib.sha256(content).hexdigest()!=version:raise ValueError('Base checksum failed')
    base=json.loads(content)
   state,counts=assemble(bundle,base)
   return materialize(state,counts,output)
  finally:fcntl.flock(lock,fcntl.LOCK_UN)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('input');a.add_argument('--output',default=str(P/'builds/import'));a.add_argument('--incremental',action='store_true');args=a.parse_args()
 try:print(json.dumps(run(args.input,args.output,args.incremental)))
 except ImportFailure as e:print(json.dumps({'status':'rejected','previous_version_retained':True,'errors':e.errors}));sys.exit(1)
 except (ValueError,KeyError,TypeError,RecursionError,AttributeError,StopIteration):print(json.dumps({'status':'rejected','previous_version_retained':True,'errors':[{'row':0,'code':'invalid_input_or_artifact','field':'input'}]}));sys.exit(1)
