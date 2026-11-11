"""Wikidata structured statements, not Wikipedia text/images. CC0 scope only."""
import json
import re
SOURCE = 'wikidata'
# No class ids are guessed here: a reviewed class/type manifest must supply them.
PROPERTIES = {'status': 'P5817', 'inception': 'P571', 'entry': 'P729', 'capacity': 'P2109',
              'cost': 'P2130', 'owner': 'P127', 'operator': 'P137', 'developer': 'P178', 'contractor': 'P1652'}


def query(class_id, offset=0, limit=100):
    if not re.fullmatch(r'Q[1-9]\d*', class_id) or offset < 0 or not 1 <= limit <= 100:
        raise ValueError('Reviewed class QID and bounded pagination required')
    # Page entity ids first; joining multivalued properties must not truncate an entity.
    return '''SELECT ?item ?itemLabel ?countryLabel ?countryCode ?coord ?alias ?statusLabel ?entry ?inception
 ?capacity ?capacityUnitLabel ?cost ?costUnitLabel ?owner ?ownerLabel ?operator ?operatorLabel
 ?developer ?developerLabel ?contractor ?contractorLabel WHERE {
 { SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:%s; wdt:P625 ?point } ORDER BY ?item LIMIT %d OFFSET %d }
 ?item wdt:P625 ?coord; wdt:P17 ?country. ?country wdt:P297 ?countryCode.
 OPTIONAL { ?item skos:altLabel ?alias FILTER(LANG(?alias)="en") }
 OPTIONAL { ?item wdt:P5817 ?status }
 OPTIONAL { ?item wdt:P571 ?inception }
 OPTIONAL { ?item wdt:P729 ?entry }
 OPTIONAL { ?item p:P2109/psv:P2109 ?cq. ?cq wikibase:quantityAmount ?capacity; wikibase:quantityUnit ?capacityUnit }
 OPTIONAL { ?item p:P2130/psv:P2130 ?costq. ?costq wikibase:quantityAmount ?cost; wikibase:quantityUnit ?costUnit }
 OPTIONAL { ?item wdt:P127 ?owner } OPTIONAL { ?item wdt:P137 ?operator }
 OPTIONAL { ?item wdt:P178 ?developer } OPTIONAL { ?item wdt:P1652 ?contractor }
 SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}''' % (class_id, limit, offset)


def parse(path, spec):
    data = json.loads(path.read_text())
    if spec.get('retained_snapshot'):
        # Migration of the existing site snapshot, not a new primary-source verification.
        # Old y was an inception year, NOT a status year; quarantine it rather than relabel it.
        out = []
        for p in data['projects']:
            row = {k: v for k, v in p.items() if v is not None and k not in ('wiki', 'y')}
            row['t'], row['sub'] = ('Real estate', p['t']) if p['t'] in ('Tower', 'Mixed-use', 'Urban regeneration') else (p['t'], None)
            if row['sub'] is None: row.pop('sub')
            row['src'] = [dict(name=spec['name'], url='https://www.wikidata.org/wiki/' + p['k'],
                               licence=spec['licence'], checked_at=spec['checked_at'], field_list=sorted(row),
                               review='Inherited site snapshot; not re-fetched. Status not independently reviewed.')]
            out.append(row)
        return out
    rows = {}
    for b in data['results']['bindings']:
        v = lambda k: b.get(k, {}).get('value')
        qid = (v('item') or '').rsplit('/', 1)[-1]
        if not re.fullmatch(r'Q[1-9]\d*', qid): raise ValueError('Invalid Wikidata id')
        match = re.fullmatch(r'Point\((-?[\d.]+) (-?[\d.]+)\)', v('coord') or '')
        if not match: continue
        row = {'k': qid, 'n': v('itemLabel'), 'c': v('countryLabel'), 'cc': v('countryCode'),
               'lo': float(match[1]), 'la': float(match[2]), 't': spec['type']}
        if v('alias'): row['aliases'] = [v('alias')]
        if v('statusLabel'): row['s'] = v('statusLabel')
        # P571 does not establish construction/commissioning; only service entry supplies status year.
        if v('entry') and (v('statusLabel') or '').casefold() in ('operational', 'in service'):
            row['y'] = int(v('entry')[:4])
        if v('capacity') and v('capacityUnitLabel') and not v('capacityUnitLabel').startswith('Q'):
            row['cap'] = {'value': float(v('capacity')), 'unit': v('capacityUnitLabel')}
        # A cost statement without a statement-specific year is deliberately excluded.
        row['own'] = [{'name': v(role+'Label'), 'role': role, 'qid': v(role).rsplit('/', 1)[-1]}
                      for role in ('owner', 'operator', 'developer', 'contractor') if v(role) and v(role+'Label')]
        if not row['own']: row.pop('own')
        row['src'] = [dict(name=spec['name'], url='https://www.wikidata.org/wiki/'+qid, licence=spec['licence'],
                          checked_at=spec['checked_at'], field_list=sorted(row))]
        if qid in rows:
            old = rows[qid]
            if (old['la'], old['lo'], old['cc']) != (row['la'], row['lo'], row['cc']):
                raise ValueError('Conflicting Wikidata places: ' + qid)
            for field in ('s', 'y', 'cap', 'cost'):
                if field in old and field in row and old[field] != row[field]:
                    raise ValueError('Conflicting Wikidata statements: '+qid+'/'+field)
            for field in ('aliases', 'own'):
                for value in row.get(field, []):
                    if value not in old.setdefault(field, []): old[field].append(value)
            for field, value in row.items():
                if field not in old: old[field] = value
            old['src'][0]['field_list'] = sorted(k for k in old if k != 'src')
        else: rows[qid] = row
    return list(rows.values())
