"""Company registry and ownership graph from the GEM Global Energy Ownership Tracker (CC BY 4.0).

Entities are joined by GEM Entity ID. A name is used only when a power-tracker row has no ID, and
only when the exact normalised name is unique in the registry; such matches are marked match='name'.
"""
import re
from collections import defaultdict

BLANK = {'', 'none', 'not found', 'unknown', '--'}


def clean(v):
    s = '' if v is None else str(v).strip()
    return None if s.lower() in BLANK else s


def norm(name):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (name or '').lower().replace('&', ' and '))).strip()


def pct(v):
    s = clean(v)
    if s is None:
        return None
    try:
        return float(s.rstrip('%'))
    except ValueError:
        return None


def split_owners(names, ids):
    """'A [65%]; B [35%]' + 'E1 [65%]; E2 [35%]' -> [{name, entity_id, stake}]. IDs align by position."""
    parts = [p.strip() for p in (clean(names) or '').split(';') if p.strip()]
    id_parts = [p.strip() for p in (clean(ids) or '').split(';') if p.strip()]
    out = []
    for i, p in enumerate(parts):
        m = re.match(r'^(.*?)\s*(?:\[([\d.]+)%\])?$', p)
        eid = None
        if len(id_parts) == len(parts):
            em = re.match(r'^(E\d+)', id_parts[i])
            eid = em.group(1) if em else None
        name = m.group(1).strip()
        if norm(name) in ('unknown', 'small shareholder s', 'natural person s', 'other'):
            continue
        out.append({'name': name, 'entity_id': eid, 'stake': float(m.group(2)) if m.group(2) else None})
    return out


class Registry:
    def __init__(self, entity_rows, edge_rows):
        """entity_rows: dicts keyed by the All Entities header; edge_rows: Entity Ownership dicts."""
        self.entities, self.by_name = {}, defaultdict(set)
        for r in entity_rows:
            eid = clean(r.get('Entity ID'))
            if not eid:
                continue
            e = {'id': eid, 'name': clean(r.get('Name')) or clean(r.get('Full Name')), 'full_name': clean(r.get('Full Name')),
                 'type': clean(r.get('Entity Type')), 'listed': str(r.get('PubliclyListed')) == 'True',
                 'lei': clean(r.get('Global Legal Entity Identifier Index')), 'cik': clean(r.get('US SEC Central Index Key')),
                 'eia': clean(r.get('US-EIA')), 'hq_country': clean(r.get('Headquarters Country')),
                 'reg_country': clean(r.get('Registration Country')), 'home_page': clean(r.get('Home Page')),
                 'status': clean(r.get('Entity Status'))}
            self.entities[eid] = e
            for n in {e['name'], e['full_name']}:
                if n:
                    self.by_name[norm(n)].add(eid)
        self.up = defaultdict(list)
        for r in edge_rows:
            child, parent = clean(r.get('Subject Entity ID')), clean(r.get('Interested Party ID'))
            if child and parent:
                self.up[child].append({'parent': parent, 'stake': pct(r.get('% Share of Ownership')),
                                       'source_url': clean(r.get('Data Source URL')),
                                       'imputed': 'imputed value' == clean(r.get('Share Imputed?'))})

    def resolve(self, owner):
        """Return (entity, match) where match is 'id', 'name' or None."""
        if owner.get('entity_id') in self.entities:
            return self.entities[owner['entity_id']], 'id'
        hits = self.by_name.get(norm(owner['name']), set())
        if len(hits) == 1:
            return self.entities[next(iter(hits))], 'name'
        return None, None

    def exposures(self, owner, max_depth=6):
        """Candidate exposures of one immediate owner: itself if listed (E1), else listed ancestors (E3)."""
        ent, match = self.resolve(owner)
        if not ent:
            return []
        if ent['listed']:
            return [self._exposure('E1', ent, [ent['id']], [], owner['stake'], match)]
        out, seen, frontier = [], {ent['id']}, [(ent['id'], [ent['id']], [], owner['stake'])]
        for _ in range(max_depth):
            nxt = []
            for node, path, edges, stake in frontier:
                for e in self.up.get(node, []):
                    p = e['parent']
                    if p in seen or p not in self.entities:
                        continue
                    seen.add(p)
                    s = None if stake is None or e['stake'] is None else round(stake * e['stake'] / 100, 4)
                    step = (path + [p], edges + [[node, p]], s)
                    if self.entities[p]['listed']:
                        ex = self._exposure('E3', self.entities[p], step[0], step[1], s, match)
                        ex['edge_sources'] = [next((x for x in self.up[c] if x['parent'] == q), {}) for c, q in step[1]]
                        out.append(ex)  # GEM rule: stop at the lowest listed company in each branch
                    else:
                        nxt.append((p,) + step)
            frontier = nxt
        return out

    def _exposure(self, kind, listed, path, edges, stake, match):
        return {'type': kind, 'listed_entity_id': listed['id'], 'listed_name': listed['name'], 'lei': listed['lei'],
                'cik': listed['cik'], 'hq_country': listed['hq_country'], 'path': path,
                'path_names': [self.entities[p]['name'] for p in path], 'path_edges': edges,
                'effective_stake': stake, 'owner_match': match}
