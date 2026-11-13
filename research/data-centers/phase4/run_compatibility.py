"""Reproduce the read-only Energy normalizer and all-record wrapper comparison."""
import json,subprocess,time
from pathlib import Path
from sector_adapter import wrap_energy,digest
P=Path(__file__).resolve().parent
subprocess.run(['node',str(P/'energy-compatibility.mjs')],check=True)
x=json.loads((P/'sources/energy-normalized.body').read_text());meta=json.loads((P/'energy-snapshot.json').read_text());raw={r['id']:r for r in x['raw']['projects']};start=time.perf_counter();before=digest(x)
for row in x['normal']:
 wrapped=wrap_energy(raw[row['id']],row,meta)
 assert wrapped['legacy_energy']==row
 for exposure,original in zip(wrapped['exposures'],raw[row['id']]['exposures']):assert exposure['verification']==original['verification']
 if raw[row['id']].get('stage')=='Pre-construction':assert wrapped['status']['stage']=='planning'
assert digest(x)==before
report=json.loads((P/'energy-compatibility.json').read_text());report.update(wrapper_records_validated=len(x['normal']),all_legacy_outputs_preserved=True,source_bundle_unchanged=True,wrapper_validation_total_ms=round((time.perf_counter()-start)*1000,2));(P/'energy-compatibility.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
