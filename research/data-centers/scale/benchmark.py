"""Deterministic backend volume tests. Does not create or measure a Projects UI."""
import copy,gzip,json,statistics,tempfile,time,tracemalloc
from pathlib import Path
from make_fixtures import bundle
from import_projects import assemble,materialize
from catalog import Catalog
P=Path(__file__).resolve().parent

def timed(fn,n=20):
 samples=[]
 for _ in range(n):
  t=time.perf_counter();fn();samples.append((time.perf_counter()-t)*1000)
 return {'median_ms':round(statistics.median(samples),3),'p95_ms':round(sorted(samples)[int(.95*(len(samples)-1))],3)}
def build():
 results=[]
 for count in [200,500,1000,5000]:
  with tempfile.TemporaryDirectory(prefix='investedia-scale-') as root:
   b=bundle(count);tracemalloc.start();t=time.perf_counter();state,counts=assemble(b);validated_ms=(time.perf_counter()-t)*1000;t=time.perf_counter();result=materialize(state,counts,root);build_ms=(time.perf_counter()-t)*1000;peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop();t=time.perf_counter();cat=Catalog(root);load_ms=(time.perf_counter()-t)*1000
   assert cat.query(limit=1)['total']==count
   assert cat.query(sector='data_centers')['total']==count//2
   groups=cat.clusters(cell_degrees=10);assert sum(c['count'] for c in groups['clusters'])==count
   first=cat.rows[0];assert cat.get(first['id'])['synthetic'] is True
   path=Path(root)/'versions'/result['version'];catalog=(path/'catalog.json').read_bytes();shard=(path/'details'/f"{first['shard']}.json").read_bytes()
   changed=copy.deepcopy(b['records'][0]);changed['name']='SYNTHETIC incremental update';new,delta=assemble({'schema':b['schema'],'synthetic':True,'records':[changed]},state);assert delta['updated']==1
   materialize(new,delta,root);newcat=Catalog(root);assert newcat.get(changed['id'])['name']==changed['name']
   newfiles=json.loads((newcat.path/'manifest.json').read_text())['files'];oldfiles=json.loads((path/'manifest.json').read_text())['files'];changed_shards=sum(newfiles.get(k)!=h for k,h in oldfiles.items() if k.startswith('details/'));assert changed_shards==1
   results.append({'records':count,'synthetic':True,'validation_ms':round(validated_ms,2),'artifact_build_ms':round(build_ms,2),'peak_traced_mib':round(peak/1024**2,2),'catalog_load_ms':round(load_ms,2),'query':timed(lambda:cat.query(q='synthetic',sector='data_centers',status='planning')),'cluster':timed(lambda:cat.clusters(cell_degrees=10)),'detail_cached':timed(lambda:cat.get(first['id'])),'catalog_bytes':len(catalog),'catalog_gzip_bytes':len(gzip.compress(catalog,mtime=0)),'selected_detail_shard_bytes':len(shard),'shards_changed_by_one_record_update':changed_shards,'clusters':len(groups['clusters']),'rendering_measured':False})
 return results
if __name__=='__main__':
 rows=build();(P/'scale-results.json').write_text(json.dumps({'scope':'Backend validation, artifact generation, filtering, geographic clustering and lazy loading only; no UI/rendering benchmark','results':rows},indent=2)+'\n');print(json.dumps(rows))
