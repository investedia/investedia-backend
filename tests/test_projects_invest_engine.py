"""Batch verification engine: extractors, matcher, classifier and safeguards. Offline fixtures only."""
import unittest

from tools.projects.invest.engine import extract
from tools.projects.invest.engine.classify import classify, quarter_end, safeguards
from tools.projects.invest.engine.match import candidates_for, core

DOC = {'kind': 'company', 'date': '2026-06-30', 'publisher': 'Fixture Power', 'url': 'https://example.org/report.pdf'}
TODAY = '2026-11-12'


def proj(name, mw=100.0, country='Saudi Arabia', **kw):
    p = {'id': 'gem:' + name, 'name': name, 'mw': mw, 'country': country, 'cc': 'SA', 'stage': 'Pre-construction'}
    p.update(kw)
    return p


class Engine(unittest.TestCase):
    def test_phase_numbers_must_match_exactly(self):
        rows = [{'doc_name': 'Rabigh 4 IWP', 'pct': 45.0, 'mw': None}]
        self.assertEqual(candidates_for(rows[0], [proj('Rabigh 2 IPP power station')]), [])
        self.assertEqual([k for _, k in candidates_for({'doc_name': 'Aral 1 Wind'}, [proj('Aral wind farm')])], ['phase'])
        self.assertEqual([k for _, k in candidates_for({'doc_name': 'Nairyah1'}, [proj('Nairyah 1 power plant')])], ['exact'])

    def test_country_and_state_must_agree(self):
        self.assertEqual(candidates_for({'doc_name': 'Thakadu, South Africa', 'comma_country': True}, [proj('Thakadu solar farm', country='Egypt')]), [])
        self.assertTrue(candidates_for({'doc_name': 'Ground Mounted Solar Project, Ganjam', 'mw': 40}, [proj('Ganjam solar farm', country='India')]))
        self.assertEqual([k for _, k in candidates_for({'doc_name': 'Jalaun Ultra Mega Solar Park 1200 MW'}, [proj('Jalaun solar park')])], ['loose'])
        us = proj('Keydet solar', country='United States', cc='US', state='VA')
        self.assertTrue(candidates_for({'doc_name': 'Keydet', 'location': 'US-VA'}, [us]))
        self.assertEqual(candidates_for({'doc_name': 'Keydet', 'location': 'US-NC'}, [us]), [])
        self.assertEqual(candidates_for({'doc_name': 'Keydet', 'location': 'US-Various'}, [us]), [])

    def test_stake_is_never_invented_and_conflicts_are_held(self):
        e = {'effective_stake': 50.0, 'listed_name': 'Fixture Power', 'hq_country': 'Germany'}
        row = {'doc_name': 'Alpha', 'pct': 35.0, 'mw': 100.0, 'cod': 'Q4 2027'}
        self.assertEqual(classify(proj('Alpha'), e, row, 'exact', DOC, TODAY)[0], 'C')
        cat, _, stake = classify(proj('Alpha'), dict(e, effective_stake=None), dict(row, pct=None), 'exact', DOC, TODAY)
        self.assertEqual((cat, stake), ('A', None))

    def test_capacity_phase_operating_and_stale_rules(self):
        e = {'effective_stake': None}
        row = {'doc_name': 'Alpha', 'pct': 40.0, 'mw': 100.0, 'cod': 'Q4 2027'}
        self.assertEqual(classify(proj('Alpha', mw=300.0), e, row, 'exact', DOC, TODAY)[0], 'C')
        self.assertEqual(classify(proj('Alpha'), e, row, 'phase', DOC, TODAY)[0], 'C')
        self.assertEqual(classify(proj('Alpha'), e, dict(row, cod='Q1 2026'), 'exact', DOC, TODAY)[0], 'D')
        self.assertEqual(classify(proj('Alpha'), e, row, 'exact', dict(DOC, date='2024-12-31'), TODAY)[0], 'C')
        self.assertEqual(classify(proj('Alpha'), e, row, 'exact', dict(DOC, kind='news'), TODAY)[0], 'C')
        self.assertEqual(classify(proj('Alpha'), e, row, 'exact', dict(DOC, kind='regulator'), TODAY)[0], 'B')

    def test_half_year_dates(self):
        self.assertEqual(quarter_end('2H 2026').month, 12)
        self.assertEqual(quarter_end('2H 2027 - 1H 2028').year, 2027)
        self.assertEqual(quarter_end('Q2 2027').month, 6)

    def test_owner_decisions_keep_some_links_internal(self):
        self.assertTrue(safeguards({'hq_country': 'Russia', 'listed_name': 'Mosenergo'}))
        self.assertTrue(safeguards({'hq_country': 'Belgium', 'listed_name': 'KBC Groep'}))
        self.assertEqual(safeguards({'hq_country': 'Saudi Arabia', 'listed_name': 'ACWA Power'}), [])

    def test_table_extractor_wrapped_names_components_and_footnotes(self):
        text = ('Saguling Float-   Indone-\n'
                '                     1         225       49.00%       60         -   Q4 2026\n'
                'ing PV IPP          sia\n')
        spec = {'row': r'^(?P<lead>.{0,30}?)\s+(?P<n>\d)\s+(?P<cost>[\d,]+)\s+(?P<pct>[\d.]+)%\s+(?P<mw>[\d,]+|-)\s', 'name_window': 16}
        r = extract.table(text, spec)[0]
        self.assertEqual((r['doc_name'], r['pct'], r['mw'], r['cod']), ('Saguling Floating PV IPP', 49.0, 60.0, 'Q4 2026'))
        aes = 'Bellefield 2 US-CA Solar 500  75  % 2H 2026\nEnergy Storage 500\nNext US-TX Wind 80  75  % 1H 2026\n'
        spec = {'row': r'^(?P<name>[A-Z][A-Za-z0-9 ]+?) (?P<loc>US-[A-Z]{2}) (?P<tech>Solar|Wind) (?P<mw>[\d,]+)\s+(?P<pct>\d+)\s+%',
                'continuation': r'^(?P<tech>Energy Storage|Solar|Wind) (?P<mw>[\d,]+)$', 'cod': r'[12]H 20\d\d'}
        rows = extract.table(aes, spec)
        self.assertEqual([(x['doc_name'], x['mw'], x['location']) for x in rows], [('Bellefield 2', 1000.0, 'US-CA'), ('Next', 80.0, 'US-TX')])

    def test_prose_needs_company_role_near_the_project_name(self):
        text = 'Heilbronn site. EnBW is building a hydrogen-ready plant at the site. It has 675 MW. Weather was fine.'
        hit = extract.prose_for(text, 'Heilbronn power station', core, ['EnBW'])
        self.assertEqual(hit['mw'], 675.0)
        self.assertIsNone(extract.prose_for('Heilbronn is a city. ' + 'Filler. ' * 10 + 'EnBW is building elsewhere.', 'Heilbronn power station', core, ['EnBW']))
        self.assertIsNone(extract.prose_for('Heilbronn plant, operated by EnBW, 675 MW.', 'Heilbronn power station', core, ['EnBW']))


if __name__ == '__main__':
    unittest.main()
