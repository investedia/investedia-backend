"""Reconcile current records without collapsing separate units or choosing conflicts."""
import collections
import copy
import difflib
from tools.projects.build_projects import canonical,distance


def identity(row):
    return {(namespace,str(value)) for namespace,value in row.get('external_ids',{}).items()
            if not namespace.endswith(':site')}


def publishers(row):
    return {key.split(':',1)[0] for key in row.get('external_ids',{})}


def reconcile(rows):
    output=[];conflicts=[];merges=[];drops=[];blocked=set();withheld=collections.defaultdict(set);blocked_ids=set()
    for raw in sorted(rows,key=lambda r:r['k']):
        row=copy.deepcopy(raw)
        if row['k'] in blocked or identity(row)&blocked_ids:
            drops.append({'id':row['k'],'reason':'quarantined-identity'});continue
        candidates=[]
        for current in output:
            exact=current['k']==row['k'] or bool(identity(current)&identity(row))
            # Distinct units and same-provider ids cannot be equated by a similar plant name.
            fuzzy=(not publishers(current)&publishers(row) and current.get('record_level')!='unit' and row.get('record_level')!='unit'
                   and current['t']==row['t'] and current['cc']==row['cc'] and distance(current,row)<2
                   and difflib.SequenceMatcher(None,canonical(current['n']),canonical(row['n'])).ratio()>=.85)
            if exact or fuzzy:candidates.append((current,'exact-id' if exact else 'name-distance-type'))
        if not candidates:output.append(row);continue
        if len(candidates)>1:
            conflicts.append({'id':row['k'],'reason':'ambiguous-cross-source-identity','candidates':[p['k'] for p,_ in candidates]})
            drops.append({'id':row['k'],'reason':'ambiguous-cross-source-identity'});continue
        current,method=candidates[0]
        bad=[field for field in ('t','cc','record_level','s','completion_date','status_date')
             if current.get(field) is not None and row.get(field) is not None and current[field]!=row[field]]
        if (current['la'],current['lo'])!=(row['la'],row['lo']):bad.append('coordinates')
        for namespace,value in current.get('external_ids',{}).items():
            if namespace in row.get('external_ids',{}) and row['external_ids'][namespace]!=value:bad.append('identity:'+namespace)
        if bad:
            conflicts.append({'id':current['k'],'other':row['k'],'fields':bad,'action':'both held out; no guess'})
            for p in (current,row):
                blocked.add(p['k']);blocked_ids.update(identity(p));drops.append({'id':p['k'],'reason':'cross-source-conflict'})
            output.remove(current);continue
        for field in ('cap','cost','own'):
            if field in current and field in row and current[field]!=row[field]:
                conflicts.append({'id':current['k'],'other':row['k'],'field':field,'action':'field withheld'})
                withheld[current['k']].add(field)
                current.pop(field);row.pop(field)
        for field,value in row.items():
            if field=='src':
                for source in value:
                    if source not in current['src']:current['src'].append(source)
            elif field=='external_ids':current.setdefault(field,{}).update(value)
            elif field=='aliases':current[field]=sorted(set(current.get(field,[]))|set(value))
            elif field not in current and field not in withheld[current['k']]:current[field]=value
        merges.append({'kept':current['k'],'merged':row['k'],'rule':method})
    return sorted(output,key=lambda r:r['k']),conflicts,merges,drops
