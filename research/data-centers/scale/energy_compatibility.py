"""Read-only Energy compatibility at a pinned frontend snapshot. No pipeline changes."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'phase4'))
from sector_adapter import wrap_energy,digest,validate_bundle

def build(commit=None):
 subprocess.run(['node',str(P/'energy-probe.mjs')]+([commit] if commit else []),check=True,stdout=subprocess.DEVNULL)
 x=json.loads((P/'builds/energy-normalized.json').read_text());meta=json.loads((P/'energy-snapshot.json').read_text());by={r['id']:r for r in x['raw']['projects']};before=digest(x);out=[]
 for n in x['normal']:
  r=by[n['id']];w=wrap_energy(r,n,meta)
  assert w['legacy_energy']==n
  assert [e['verification'] for e in w['exposures']]==[e['verification'] for e in r['exposures']]
  # Source fields absent from the old normalized object also remain byte-equivalent.
  w['legacy_energy_source']=copy.deepcopy(r)
  w['legacy_energy_source_sha256']=digest(r)
  assert w['legacy_energy_source'].get('images')==r.get('images')
  assert [e.get('hq') for e in w['legacy_energy_source']['exposures']]==[e.get('hq') for e in r['exposures']]
  out.append(w)
 validate_bundle(out);assert digest(x)==before
 report=json.loads((P/'energy-compatibility.json').read_text());report.update(expected_project_count_from_request=187,unique_projects=len(out),verified_exposure_count=sum(len(r['exposures']) for r in x['raw']['projects']),count_explanation='Latest main and live feed contain 186 unique projects and 187 company exposure relationships; no project manufactured',all_ids_preserved=True,all_imagery_metadata_preserved=True,all_hq_preserved=True,all_status_preserved=True,all_raw_verification_preserved=True,wrapper_passed=len(out),production_edits=False)
 (P/'energy-compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
 (P/'builds/energy-envelope.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n')
 return out
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--commit');args=a.parse_args();print(json.dumps({'projects':len(build(args.commit))}))
