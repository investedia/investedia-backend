"""Official Projects API rows. Country-only records are retained off-map."""
import json
SOURCE = 'world_bank'
def parse(path, spec):
    data = json.loads(path.read_text())
    out = []
    for key, p in data.get('projects', {}).items():
        if key == 'total' or not isinstance(p, dict): continue
        if str(p.get('status', '')).casefold() not in ('active', 'pipeline'): continue
        # The status of a finance operation does NOT establish construction status.
        locs = p.get('locations') or []
        if isinstance(locs, dict): locs = list(locs.values())
        if not locs: locs = [{}]
        for i, loc in enumerate(locs):
            row = {'k': 'world_bank:'+str(p.get('id') or key)+(':'+str(loc.get('id', i)) if loc else ''),
                   'n': p.get('project_name') or p.get('projectname'), 't': 'Development finance',
                   'c': p.get('countryname') or p.get('countryshortname'),
                   'la': loc.get('latitude'), 'lo': loc.get('longitude'), 'location_precision': loc.get('precision')}
            row['precise_physical_location_verified'] = spec.get('record_reviews', {}).get(row['k'], {}).get('precise_physical_location_verified') is True
            # Retain the disclosed amount only when its currency and approval year are explicit.
            if p.get('totalamt') is not None and p.get('currency') and p.get('boardapprovaldate'):
                row['cost'] = {'value': float(p['totalamt']), 'currency': p['currency'], 'year': int(p['boardapprovaldate'][:4])}
            row['src'] = [dict(name=spec['name'], url=spec['url'], licence=spec['licence'],
                               checked_at=spec['checked_at'], field_list=sorted(row))]
            out.append(row)
    return out
