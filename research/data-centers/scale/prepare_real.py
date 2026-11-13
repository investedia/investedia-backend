"""Reuse earlier research without re-reviewing it or promoting release status."""
import copy,json
from pathlib import Path
P=Path(__file__).resolve().parent

def bundle():
 base=P.parent/'phase4';rows=json.loads((base/'sector-records.json').read_text())['projects'];rows=[r for r in rows if r['sector']!='energy'];rows+=json.loads((base/'real-estate-pilot.json').read_text())['projects'];out=[]
 for r in rows:
  r=copy.deepcopy(r);r['synthetic']=False;r['source_identity']={'authority':'investedia-reviewed-research','id':r['id']}
  # Adding transport metadata changes the signed fact digest. Do not silently re-sign it.
  r['reuse']['import_note']='Transport metadata added; prior record review remains in Phase4. Public export needs a fresh exact-artifact review.'
  out.append(r)
 return {'schema':'investedia.projects.import.v1','synthetic':False,'records':out}
if __name__=='__main__':
 p=P/'builds/real-import.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(bundle(),ensure_ascii=False,indent=2)+'\n');print('Prepared 15 existing research records; no release status promoted')
