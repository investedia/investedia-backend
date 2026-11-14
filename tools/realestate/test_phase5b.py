"""Phase 5B checks: contract, claims discipline, stable ids, release manifest, and local change detection
through Codex's importer using sample property events. Monitoring is never enabled.
Run: python3 -m unittest tools/realestate/test_phase5b.py (from the backend root)."""
import copy, json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); sys.path.insert(0, str(ROOT / 'research/data-centers/scale'))
from sector_adapter import validate, digest  # noqa: E402
import import_projects as imp  # noqa: E402

P5 = ROOT / 'data/realestate/phase5b'; B1 = ROOT / 'data/realestate/batch1'
ENV = json.loads((P5 / 'import-phase5b.json').read_text()); B1ENV = json.loads((B1 / 'import-batch1.json').read_text())
R = ENV['records']; MAN = json.loads((P5 / 'release-manifest.json').read_text()); REV = {x['id']: x for x in json.loads((P5 / 'release-review.json').read_text())}
FORBIDDEN = {'rent', 'rental_income', 'yield', 'valuation', 'occupancy', 'return', 'noi', 'cap_rate'}

def keys(x):
    if isinstance(x, dict):
        for k, v in x.items(): yield k; yield from keys(v)
    elif isinstance(x, list):
        for v in x: yield from keys(v)

class Contract(unittest.TestCase):
    def test_all_validate(self):
        for r in R: validate(r)
    def test_ids_stable(self):
        old = {r['id'] for r in B1ENV['records']}; new = {r['id'] for r in R}; gone = {x['id'] for x in ENV['retire']}
        self.assertEqual(old - new, gone)                       # only disposed records leave the live set
        self.assertEqual(new - old, {'re:hst:renaissance-dallas-at-plano-legacy-west-hotel', 're:hst:1-hotel-brooklyn-bridge'})
    def test_history_kept(self):
        for r in R:
            if r['id'] in {x['id'] for x in B1ENV['records']}: self.assertIn('batch1_location', r['history'])
    def test_no_title_claims(self):
        for r in R:
            self.assertFalse(r['verification']['property_title_verified'])
            for e in r['exposures']:
                self.assertNotIn(e['role'], {'direct_property_owner', 'indirect_property_owner'})
                self.assertIn('no title', e['investment_access']['scope'])
    def test_no_invented_financials(self):
        for r in R: self.assertFalse(FORBIDDEN & {k.lower() for k in keys(r)}, r['id'])
    def test_location_ladder(self):
        for r in R:
            l = r['location']
            if l['precision'] == 'exact': self.assertIn(l['point_type'], {'address_point', 'building_point'}); self.assertEqual(l['evidence']['scope'], 'specific_site')
            if l['precision'] == 'approximate': self.assertIn('not the building', l['label'])
            if l.get('satellite_allowed'): self.assertEqual(l.get('confidence'), 'high')
    def test_images_identified_and_licensed(self):
        for r in R:
            for im in r['imagery']:
                self.assertEqual(im['project_id'], r['id']); self.assertIn('visually checked', im['identity_check']); self.assertTrue(im['credit'] and im['licence'])
    def test_monitoring_disabled(self):
        for r in R: self.assertFalse(r['monitoring']['enabled']); self.assertTrue(r['monitoring']['evidence_refs'])
    def test_manifest(self):
        # owner rule (14 Nov 2026): only properties with a verified picture or a development plan
        self.assertTrue(0 < MAN['count'] <= 50); self.assertIn('not published', MAN['status'])
        byid = {r['id']: r for r in R}
        for m in MAN['records']:
            r = byid[m['id']]; self.assertEqual(REV[m['id']]['fact_sha256'], m['fact_sha256']); self.assertNotEqual(r['location']['precision'], 'unknown')
            self.assertTrue(r['imagery'] or r['status']['stage'] in ('under_construction', 'completed') or 'evelopment' in r['asset']['subtype'], m['id'])

class ChangeDetection(unittest.TestCase):
    """Sample events -> proposed record update -> importer detects exactly that change (local only)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.out = Path(self.tmp.name)
        self.state = imp.assemble({**B1ENV})[0] if isinstance(imp.assemble({**B1ENV}), tuple) else imp.assemble({**B1ENV})
    def tearDown(self): self.tmp.cleanup()
    def _apply(self, recs, retire=()):
        b = {'schema': ENV['schema'], 'synthetic': False, 'companies': ENV['companies'], 'records': recs, 'retire': list(retire)}
        return imp.assemble(b, base=self.state)
    def _counts(self, res): return res[1] if isinstance(res, tuple) else res['counts']
    def test_unchanged_evidence_is_quiet(self):
        res = self._apply([copy.deepcopy(r) for r in B1ENV['records']]); c = self._counts(res)
        self.assertEqual(c['updated'], 0); self.assertEqual(c['unchanged'], len(B1ENV['records']))
    def test_status_change_detected(self):
        r = copy.deepcopy(next(x for x in B1ENV['records'] if x['id'] == 're:bxp:290-binney-street'))
        r['status'] = {'stage': 'completed', 'label': 'sample event: placed in service', 'as_of': '2026-04-30', 'certainty': 'company_reported'}
        c = self._counts(self._apply([r])); self.assertEqual((c['updated'], c['inserted']), (1, 0))
    def test_ownership_change_detected(self):
        r = copy.deepcopy(next(x for x in B1ENV['records'] if x['id'] == 're:bxp:601-lexington-avenue'))
        e = r['exposures'][0]; ev = {**e['evidence'], 'record_id': r['id'], 'scope': 'specific_property'}
        e.update(property_stake=55.0, stake_scope='specific_property', property_evidence=ev)
        c = self._counts(self._apply([r])); self.assertEqual(c['updated'], 1)
    def test_disposal_requires_matching_hash(self):
        rid = 're:hst:sheraton-parsippany-hotel'
        good = next(x for x in ENV['retire'] if x['id'] == rid)
        c = self._counts(self._apply([], [good])); self.assertEqual(c['retired'], 1)
        with self.assertRaises(imp.ImportFailure): self._apply([], [{**good, 'expected_sha256': '0' * 64}])
    def test_acquisition_inserted(self):
        r = next(x for x in R if x['id'] == 're:hst:1-hotel-brooklyn-bridge')
        c = self._counts(self._apply([copy.deepcopy(r)])); self.assertEqual(c['inserted'], 1)

if __name__ == '__main__': unittest.main()
