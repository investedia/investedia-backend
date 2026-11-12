"""Local GLEIF index from the golden copy (CC0): exact legal-name lookup and parent relationships.

python -m tools.projects.invest.engine.gleif_local <lei2.csv.zip> <rr.csv.zip>
Writes data/projects/raw/invest/gleif/index.sqlite. Only ACTIVE entities with ISSUED or LAPSED registrations;
only ACTIVE consolidation relationships. Names are matched by key() (case, punctuation and legal-form
suffixes ignored); a key that maps to several entities in the same country is ambiguous and not used.
"""
import csv, io, sqlite3, sys, zipfile
from pathlib import Path

from .route_b_us import key

DB = Path(__file__).resolve().parents[4] / 'data/projects/raw/invest/gleif/index.sqlite'


def _rows(zpath):
    z = zipfile.ZipFile(zpath)
    name = next(n for n in z.namelist() if n.endswith('.csv'))
    yield from csv.DictReader(io.TextIOWrapper(z.open(name), encoding='utf-8', newline=''))


def build(lei2, rr):
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    db = sqlite3.connect(DB)
    db.executescript('CREATE TABLE e(lei TEXT PRIMARY KEY, name TEXT, k TEXT, country TEXT, jurisdiction TEXT, reg TEXT);'
                     'CREATE TABLE r(child TEXT, parent TEXT, kind TEXT);')
    batch = []
    for r in _rows(lei2):
        if r.get('Entity.EntityStatus') != 'ACTIVE' or r.get('Registration.RegistrationStatus') not in ('ISSUED', 'LAPSED', 'PENDING_TRANSFER', 'PENDING_ARCHIVAL'):
            continue
        n = r['Entity.LegalName']
        batch.append((r['LEI'], n, key(n), r['Entity.LegalAddress.Country'], r.get('Entity.LegalJurisdiction'), r['Registration.RegistrationStatus']))
        if len(batch) >= 50000:
            db.executemany('INSERT OR REPLACE INTO e VALUES (?,?,?,?,?,?)', batch); batch = []
    db.executemany('INSERT OR REPLACE INTO e VALUES (?,?,?,?,?,?)', batch)
    rel = []
    for r in _rows(rr):
        t = r.get('Relationship.RelationshipType')
        if t in ('IS_DIRECTLY_CONSOLIDATED_BY', 'IS_ULTIMATELY_CONSOLIDATED_BY') and r.get('Relationship.RelationshipStatus') == 'ACTIVE':
            rel.append((r['Relationship.StartNode.NodeID'], r['Relationship.EndNode.NodeID'], 'direct-parent' if t.startswith('IS_DIRECTLY') else 'ultimate-parent'))
    db.executemany('INSERT INTO r VALUES (?,?,?)', rel)
    db.executescript('CREATE INDEX ek ON e(k, country); CREATE INDEX rc ON r(child);')
    db.commit()
    return db.execute('select count(*) from e').fetchone()[0], len(rel)


class Index:
    def __init__(self):
        self.db = sqlite3.connect(DB)

    def by_name(self, name, country='US'):
        hits = self.db.execute('select lei,name from e where k=? and country=?', (key(name), country)).fetchall()
        return hits[0] if len(hits) == 1 else None

    def name(self, lei):
        r = self.db.execute('select name from e where lei=?', (lei,)).fetchone()
        return r[0] if r else None

    def parent(self, lei, kind):
        r = self.db.execute('select parent from r where child=? and kind=?', (lei, kind)).fetchone()
        return r[0] if r else None


if __name__ == '__main__':
    print(build(sys.argv[1], sys.argv[2]))
