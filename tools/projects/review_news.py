"""Produce a deterministic, unlabelled review sample. Does not approve itself or write articles."""
import json
import random
from pathlib import Path
from tools.projects.news_links import candidates, fingerprint
from tools.projects.build_projects import ROOT

def main():
    projects=json.loads((ROOT/'assets/globe/projects.json').read_text())['projects']
    articles={}
    for name in ('news-live.json','news-48h.json','news-archive.json'):
        for a in json.loads((ROOT/'assets/globe'/name).read_text()).get('stories',[]): articles[a['id']]=a
    rows=candidates(list(articles.values()),projects,json.loads((ROOT/'assets/globe/iso.json').read_text()))
    rows.sort(key=lambda r:(r['event'],r['project']));random.Random(19).shuffle(rows)
    sample=[{'event':r['event'],'project':r['project'],'headline':r['headline'],
             'source_url':(r.get('source') or {}).get('url'),'evidence':r['evidence'],'correct':None} for r in rows[:100]]
    out={'enabled':False,'dataset_sha256':fingerprint(projects),'reviewer':None,'checked_at':None,
         'candidate_matches':len(rows),'sample':sample,'accuracy_pct':None,
         'reason':'Human review required; no synthetic matches count toward acceptance'}
    path=ROOT/'data/projects/news-match-review.json';path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'candidates':len(rows),'sampled':len(sample),'accuracy_pct':None,'enabled':False}))
if __name__=='__main__':main()
