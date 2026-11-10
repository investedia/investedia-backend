"""Manual runner entry. --fetch only in Actions; --input for offline replay."""
import argparse,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from tools.markets_pilot.fetch import Downloads,collect
from tools.markets_pilot.registry import build,write,MIC_COUNTRY
ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--fetch',action='store_true');group.add_argument('--input',type=Path)
 p.add_argument('--workspace',type=Path,default=ROOT/'.local/markets-pilot');p.add_argument('--max-download-mb',type=int,default=6144);a=p.parse_args()
 if not 256<=a.max_download_mb<=8192:p.error('download_budget_must_be_256_to_8192_MiB')
 if a.fetch and os.environ.get('GITHUB_ACTIONS')!='true':p.error('downloads_only_on_manual_Actions_runner')
 try:
  if a.fetch:
   exchanges=json.loads((ROOT/'data/exchanges.json').read_text());exchanges={k:{field:v.get(field) for field in ('name','short','country','timezone','sessions','calendar')} for k,v in exchanges.items() if k in MIC_COUNTRY}
   downloads=Downloads(a.workspace/'raw',a.max_download_mb*1024**2);raw=collect(downloads,exchanges)
  else:raw=json.loads(a.input.read_text())
  manifest,path=build(raw,a.workspace)
  result={'status':'validated','version':manifest['version'],'publication_eligible':manifest['publication_eligible'],'coverage':manifest['coverage'],'bytes':manifest['stored_bytes']}
  write(a.workspace/'build-result.json',result)
  output=os.environ.get('GITHUB_OUTPUT')
  if output:
   with open(output,'a') as f:f.write('version='+manifest['version']+'\n')
  print(json.dumps(result));return 0
 except (Exception,KeyboardInterrupt) as error:
  # Do not print provider responses, credentials, or partial raw personal data.
  code=str(error) if isinstance(error,ValueError) and str(error).replace('_','').replace(':','').replace('-','').isalnum() else type(error).__name__
  write(a.workspace/'build-result.json',{'status':'failed','reason':code,'last_good_replaced':False})
  print('Markets pilot build failed; inspect build-result.json and reports. Last good version retained.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
