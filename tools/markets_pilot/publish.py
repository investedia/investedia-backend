"""Explicit owner-operated publication only. Default emits a plan, never writes cloud state.
Uses an already authenticated Wrangler installation; no credentials in arguments.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from tools.markets_pilot.registry import write
VERSION=re.compile(r'^\d{8}T\d{6}Z-[0-9a-f]{12}$')

def plan(directory,bucket,namespace,previous=None):
 root=Path(directory).resolve();manifest=json.loads((root/'manifest.json').read_text())
 if not VERSION.fullmatch(manifest.get('version','')) or not manifest.get('publication_eligible') or manifest.get('fixture'):raise ValueError('artifact_not_eligible_for_publication')
 if not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]',bucket):raise ValueError('invalid_bucket_name')
 if not re.fullmatch('[a-f0-9]{32}',namespace):raise ValueError('invalid_KV_namespace_id')
 prefix='markets/'+manifest['version']
 commands=[]
 for name,info in manifest['files'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or not path.is_file():raise ValueError('unsafe_or_missing_artifact_file')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('artifact_checksum_mismatch')
  commands.append(['wrangler','r2','object','put',bucket+'/'+prefix+'/'+name,'--file',str(path),'--remote'])
 commands.append(['wrangler','r2','object','put',bucket+'/'+prefix+'/manifest.json','--file',str(root/'manifest.json'),'--remote'])
 old=previous.get('version') if previous else None
 if old and not VERSION.fullmatch(old):raise ValueError('invalid_previous_version')
 pointer={'version':manifest['version'],'previous_version':old,'updated_at':manifest['updated_at']}
 return commands,pointer


def execute(commands,pointer,namespace,pointer_file,runner=subprocess.run):
 # Activation is last: a failed upload never replaces the current KV pointer.
 for args in commands:
  result=runner(args,capture_output=True,text=True)
  if result.returncode:raise ValueError('R2_upload_failed_pointer_not_changed')
 write(pointer_file,pointer)
 result=runner(['wrangler','kv','key','put','markets:current','--namespace-id',namespace,'--path',str(pointer_file),'--remote'],capture_output=True,text=True)
 if result.returncode:raise ValueError('pointer_activation_failed_check_provider_state')


def main():
 p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--bucket',required=True);p.add_argument('--namespace',required=True);p.add_argument('--previous-pointer',type=Path)
 p.add_argument('--execute',action='store_true');p.add_argument('--confirm');p.add_argument('--plan',type=Path,default=Path('.local/markets-publish-plan.json'));a=p.parse_args()
 try:
  previous=json.loads(a.previous_pointer.read_text()) if a.previous_pointer else None
  commands,pointer=plan(a.artifact,a.bucket,a.namespace,previous)
  write(a.plan,{'mode':'plan-only','object_uploads':len(commands),'pointer':pointer,'activation_last':True,'no_cloud_writes_performed':True})
  if not a.execute:print('Publication plan saved; no cloud writes.');return 0
  if a.confirm!='MARKETS-PUBLISH':raise ValueError('explicit_MARKETS_PUBLISH_confirmation_required')
  execute(commands,pointer,a.namespace,a.plan.with_name('markets-pointer.json'))
  print('Versioned uploads acknowledged; active pointer written. API flag unchanged.');return 0
 except (ValueError,OSError):print('Markets publication incomplete; no success claimed. Inspect provider state without exposing credentials.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
