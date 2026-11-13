"""Per-record publication gates, isolated adapter projection and local preview assets."""
import copy,csv,hashlib,json
from pathlib import Path
from adapter import normalize,classify
P=Path(__file__).resolve().parent
B=P.parent
PRIORITY={'project:eqix:MD5':'Q2807','project:eqix:SV18':'Q16553','project:eqix:SG6':'Q334','project:coresite:DE3':'Q16554','project:coresite:NY3':'Q1013249'}

def build():
 d=json.loads((B/'phase2/phase2-dataset.json').read_text());records=d['original_records']+d['development_records'];cities=json.loads((P/'city-references.json').read_text());headquarters=json.loads((P/'headquarters-references.json').read_text())['companies'];decisions=json.loads((P/'reuse-decisions.json').read_text());contract=json.loads((P/'schema-contract.json').read_text())
 matrices=[];preview=[];public=[]
 for r in records:
  rid=r['id'];context=r.get('count_as_project') is False;economic=bool(r.get('economic_relationships'));company=d['companies'].get(r['company'],{});location=copy.deepcopy(cities[PRIORITY[rid]]) if rid in PRIORITY else None
  blocks=[];notes=[]
  if context:blocks.append({'code':'context_not_individual_project','detail':'Parent/JV programme; excluded from project count. Preserve only as background context.'})
  if not economic:blocks.append({'code':'economic_relationship_unproven','detail':r.get('phase2_review',{}).get('disposition','Only a source affiliation is established.')})
  if r.get('original_category')=='D':blocks.append({'code':'source_identity_country_conflict','detail':'Original official source assigns Dublin to UK; contradiction not silently fixed.'})
  if not r.get('status'):blocks.append({'code':'stage_unverified','detail':'No documented operating/development stage; directory publication is insufficient.'})
  if r.get('target_warning'):blocks.append({'code':'current_stage_needs_confirmation','detail':r['target_warning']})
  if not company.get('listing_verified') or company.get('security_type')!='common_equity':blocks.append({'code':'current_common_equity_unverified','detail':'CIK/ticker/exchange/security class evidence missing.'})
  if not company.get('registry_asset_id'):blocks.append({'code':'shared_registry_mapping_missing','detail':'External SEC identifier is not a reviewed shared-registry mapping.'})
  if not location:blocks.append({'code':'location_classification_unresolved','detail':'No checked, reusable city-reference or exact-site point assigned in this pass. Company pins not silently promoted.'})
  else:notes.append('City-reference marker permitted by Phase3 owner decision; not an exact site. No satellite/crop allowed.')
  reuse=decisions.get('records',{}).get(rid,{})
  if reuse.get('status')!='cleared':blocks.append({'code':'source_reuse_decision_pending','detail':reuse.get('reason','Source-specific factual reuse and contractual/database restrictions not resolved. No table/text/image republication permission inferred.')})
  if contract.get('status')!='approved':blocks.append({'code':'sector_contract_approval_pending','detail':'Normalized adapter projection tested; live loader hardcodes Energy and ownership labels. Relation-aware hook requires coordination, no shared edit authorized.'})
  if r.get('source_conflicts'):notes.append('Only nonconflicting source-qualified facts exposed; conflicting area/target is explicitly withheld or labelled.')
  entry={'id':rid,'name':r['name'],'scope':r['project_type'],'priority':1 if rid in PRIORITY else 3 if context else 2,'exposure_class':classify(r),'blocking_count':len(blocks),
   'blockers':blocks,'notes':notes,'location':location,'economic_role_verified':economic,'public_release_eligible':not blocks,'direct_property_title_verified':bool(r.get('direct_title_evidence')),
   'imagery_compliance':'No image used. No source copyright/photo licence asserted. Approximate point cannot trigger site imagery.'}
  matrices.append(entry)
  if rid in PRIORITY and economic and location and company.get('registry_asset_id'):
   ref=headquarters.get(company['ticker']);hq={'city':ref['hq_city'],'lat':ref['hq_lat'],'lon':ref['hq_lon'],'precision':'city_reference','exact_office':False,'source_url':ref['source_url'],'source':ref['source'],'licence':ref['licence'],'checked_at':ref['checked_at']} if ref else None
   release={'eligible':not blocks,'blockers':blocks,'rights_status':reuse.get('status','pending'),'contract_status':contract['status'],'review':reuse.get('decision_evidence',{})}
   projected=normalize(r,company,location,hq,release)
   preview.append(projected)
   if not blocks:public.append(normalize(r,company,location,hq,release,for_public=True))
 matrices.sort(key=lambda r:(r['priority'],r['blocking_count'],r['id']))
 report={'schema':'investedia.data-centers.phase3-blockers.v1','records':matrices,'counts':{'reviewed_records':len(records),'development_rows':len(d['development_records']),'priority_candidates':len(preview),'public_cleared':len(public),'new_exact_sites':0,'new_approximate_city_references':len(preview),
   'direct_property_ownership_verified':sum(bool(r.get('direct_title_evidence')) for r in records),'issuer_reported_group_owned':d['counts']['issuer_reported_ownership_relationship_records'],
   'economic_asset_or_project_records':d['counts']['verified_economic_asset_or_project_records'],'operating_or_lease_original_records':sum(classify(r)=='verified_lease_or_operational_exposure' for r in d['original_records'])},
  'licensing_statement':'Individual facts are distinguished from protected expression/compilations; unresolved source contract/database conditions and adapter approval still prevent public release.'}
 (P/'blocker-matrix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 with (P/'blocker-matrix.csv').open('w',newline='') as f:
  writer=csv.writer(f,lineterminator="\n");writer.writerow(['id','name','scope','exposure_class','priority','public_eligible','blocking_codes','exact_remaining_work'])
  for row in matrices:writer.writerow([row['id'],row['name'],row['scope'],row['exposure_class'],row['priority'],row['public_release_eligible'],'; '.join(b['code'] for b in row['blockers']),' | '.join(b['detail'] for b in row['blockers'])])
 doc={'schema':'investedia.projects.data-centers.normalized-preview.v1','projects':preview,'notice':'LOCAL RESEARCH PREVIEW. City-reference markers, not exact sites. Not approved for publication. Not investment advice.'}
 (P/'adapter-preview.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n');(P/'preview/data.json').write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'\n')
 (P/'public-export.json').write_text(json.dumps({'schema':'investedia.projects.sector-release.v1','sector':'Data Centers','projects':public,'release_status':'blocked' if not public else 'data-cleared; not deployed'},indent=2)+'\n')
 print(json.dumps(report['counts']))
 return report
if __name__=='__main__':build()
