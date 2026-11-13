"""Build isolated Phase4 outputs from existing evidence; never writes production."""
import copy,csv,hashlib,json,sys
from pathlib import Path
from sector_adapter import wrap_dc,wrap_energy,validate,public_projection,digest,validate_bundle
P=Path(__file__).resolve().parent;B=P.parent

def load(path):return json.loads(path.read_text())
def write(name,value): (P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def build():
 old=load(B/'phase2/phase2-dataset.json');byid={r['id']:r for r in old['original_records']+old['development_records']};energy=load(P/'energy-snapshot.json');ready=[];dc=[];decisions=load(P/'field-reuse-review.json')
 for p in load(B/'phase3/adapter-preview.json')['projects']:
  rec=byid[p['id']];company=old['companies'][rec['company']]
  r=wrap_dc(p,rec,company,{'city_sha256':hashlib.sha256((B/'phase3/city-references.json').read_bytes()).hexdigest(),'hq_sha256':hashlib.sha256((B/'phase3/headquarters-references.json').read_bytes()).hexdigest()})
  decision=decisions['records'][r['id']]
  r['reuse']['fields']=copy.deepcopy(decision['fields']);r['reuse']['review']=copy.deepcopy(decision.get('review'))
  # Review binds these narrowly selected factual fields, not earlier marketing metrics.
  if r['reuse']['review']:
   fact=copy.deepcopy(r);fact.pop('reuse',None);fact.pop('legacy_energy',None)
   if r['reuse']['review'].get('fact_sha256')!=digest(fact):raise ValueError('Review digest stale for '+r['id'])
  validate(r);dc.append(r)
  try:ready.append(public_projection(r))
  except ValueError:pass
 e=[wrap_energy(v['raw'],v['normalized'],energy) for v in energy['projects']]
 validate_bundle(e+dc)
 write('sector-records.json',{'schema':'investedia.projects.sector-bundle.proposal.v2','contract_status':'proposed; shared integration not approved','projects':e+dc})
 write('dc-data-ready.json',{'schema':'investedia.projects.data-review.v1','status':'data-reviewed only; no shared integration or production release approved','projects':ready})
 rows=copy.deepcopy(load(B/'phase3/blocker-matrix.json')['records'])
 for row in rows:
  row['blockers']=[b for b in row['blockers'] if b['code']!='sector_contract_approval_pending']
  if row['id'] in {r['id'] for r in dc}:
   row['local_adapter_compatible']=True
   if row['id'] in {r['id'] for r in ready}:row['blockers']=[b for b in row['blockers'] if b['code']!='source_reuse_decision_pending']
   if row['id'].endswith('DE3'):row['blockers'].append({'code':'current_stage_unconfirmed','detail':'2026 availability target and development announcement do not establish current completion or operation. Discovery may show announced project, not confirmed active construction.'})
  row['data_review_cleared']=not row['blockers'];row['production_release_approved']=False;row['shared_integration_gate']='Proposed multi-sector hook and role labels need approval before shared-code changes';row['blocking_count']=len(row['blockers'])
  row.pop('public_release_eligible',None)
 write('blocker-matrix.json',{'records':rows,'data_ready_count':len(ready),'production_release_approved_count':0})
 with (P/'blocker-matrix.csv').open('w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['id','name','data_review_cleared','remaining_data_blockers','shared_integration'])
  for r in rows:w.writerow([r['id'],r['name'],r['data_review_cleared'],' | '.join(b['code']+': '+b['detail'] for b in r['blockers']),r['shared_integration_gate']])
 # Only researched DC and existing verified Energy sources in the local rendering bridge.
 preview=[]
 for r in e+dc:
  loc=r['location'];ex=r['exposures'][0];li=ex['listing'];hq=ex.get('headquarters');phase3=next((x for x in load(B/'phase3/adapter-preview.json')['projects'] if x['id']==r['id']),None)
  preview.append({'id':r['id'],'name':r['name'],'sector':{'energy':'Energy','data_centers':'Data Centers'}[r['sector']],'type':r['asset']['category'],'stage':r['status']['label'],'status':r['status'],'country':r['country_code'],'location':r['city'] or r['name'],'lat':loc['lat'],'lon':loc['lon'],'location_accuracy':loc,'listed_exposure':{'ticker':li['ticker'],'name':li['name']},'invest':{'exposures':[{'name':li['name'],'ticker':li['ticker'],'exchange':li['exchange'],'category':ex['role'],'category_label':ex['label'],'role_labels':[ex['label']],'maturity':ex.get('maturity','inherited Energy verification'),'investment_route':ex['investment_access'],'hq':{'city':hq['city'],'lat':hq['lat'],'lon':hq['lon']} if hq else None}]},'sources':[{'name':'Official project evidence','url':r['identity_evidence']['url']},{'name':'Listing evidence','url':li['evidence']['url']},{'name':'Geographic evidence','url':loc['evidence']['url']}],'capacity':None,'expected_completion':None,'review_state':'Existing verified Energy data; local integration only' if r['sector']=='energy' else 'Data review cleared; integration approval pending' if r['id'] in {x['id'] for x in ready} else 'Research preview; data reuse/stage review pending','preview_only':True,'asset':r['asset'],'reuse':r['reuse']})
 write('preview/data.json',{'projects':preview,'public_deployment_approved':False,'data_ready_dc_count':len(ready),'notice':'Local review only. No production release. Not investment advice.'})
 print(json.dumps({'data_center_candidates':len(dc),'data_review_cleared':len(ready),'energy_preview':len(e),'production_release_approved':0}))
 return e,dc,rows
if __name__=='__main__':build()
