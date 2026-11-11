"""Create a small, public basic-map copy. No paid entitlement or fake locked facts."""
import argparse
import json
from pathlib import Path

BASIC={'k','n','aliases','c','cc','la','lo','t','sub','s','display_status','y','ys','ye','status_date','status_source',
       'completion_date','cap','coordinate_precision','coordinate_quality','record_level','upd','validation_status','src','photo','satellite'}


def slim(document):
    if document.get('schema')!='investedia.projects.v2':raise ValueError('Expected v2 projects')
    rows=[]
    for project in document['projects']:
        if project.get('validation_status')!='verified':continue
        core={'k','n','lo','la','t','c','cc'}
        if not core<=set(project):raise ValueError('Incomplete basic project')
        if not all(any(field in source.get('field_list',[]) and source.get('licence') and source.get('checked_at') for source in project.get('src',[])) for field in core):
            raise ValueError('Basic project lacks field evidence')
        rows.append({key:value for key,value in project.items() if key in BASIC})
    return {'schema':document['schema'],'build_date':document['build_date'],'policy':document.get('policy'),
            'projects':rows,'notice':'Basic project facts are free. Advanced research tools are planned, not currently locked data. Not investment advice.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=Path('assets/globe/projects.json'))
    p.add_argument('--output',type=Path,default=Path('.local/projects-scale/frontend/projects.json'));args=p.parse_args()
    data=slim(json.loads(args.input.read_text()));args.output.parent.mkdir(parents=True,exist_ok=True)
    temp=args.output.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');temp.replace(args.output)
    print(json.dumps({'projects':len(data['projects']),'bytes':args.output.stat().st_size,'input_bytes':args.input.stat().st_size}))
