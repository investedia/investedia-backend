"""Projects investment layer: ownership graph, eligibility rules and export. Offline fixtures only."""
import unittest

from tools.projects.invest.build import build
from tools.projects.invest.graph import Registry, split_owners
from tools.projects.invest.rules import evaluate, exposure_problems

TODAY = '2026-11-12'
ENTITIES = [
    {'Entity ID': 'E1', 'Name': 'Listed Power', 'Full Name': 'Listed Power PLC', 'PubliclyListed': 'True', 'Global Legal Entity Identifier Index': 'LEI0001', 'Headquarters Country': 'United Kingdom'},
    {'Entity ID': 'E2', 'Name': 'Project Holdco', 'Full Name': 'Project Holdco LLC', 'PubliclyListed': 'False'},
    {'Entity ID': 'E3', 'Name': 'State Utility', 'Full Name': 'State Utility', 'PubliclyListed': 'False', 'Entity Type': 'state body'},
    {'Entity ID': 'E4', 'Name': 'Samsung C&T', 'Full Name': 'Samsung C&T Corp', 'PubliclyListed': 'True'},
    {'Entity ID': 'E5', 'Name': 'Samsung Electronics', 'Full Name': 'Samsung Electronics Co Ltd', 'PubliclyListed': 'True'},
    {'Entity ID': 'E6', 'Name': 'Twin', 'PubliclyListed': 'True'}, {'Entity ID': 'E7', 'Name': 'Twin', 'PubliclyListed': 'True'},
]
EDGES = [{'Subject Entity ID': 'E2', 'Interested Party ID': 'E1', '% Share of Ownership': '60', 'Data Source URL': 'https://example.org/annual-report', 'Share Imputed?': 'known value, not imputed'}]
ISO = {'United Kingdom': 'GB', 'United States': 'US'}


def unit(**kw):
    row = {'Type': 'wind', 'Country/area': 'United Kingdom', 'Plant / Project name': 'Fixture wind farm', 'Capacity (MW)': '100',
           'Status': 'construction', 'Start year': '2028', 'Owner(s)': 'Listed Power PLC [50%]; State Utility [50%]',
           'Owner(s) GEM Entity ID': 'E1 [50%]; E3 [50%]', 'Latitude': '51.5', 'Longitude': '-0.1', 'Location accuracy': 'exact',
           'GEM location ID': 'L1', 'GEM.Wiki URL': 'https://www.gem.wiki/Fixture'}
    row.update(kw)
    return row


def record(**kw):
    rec = {'identity': {'scheme': 'LEI', 'id': 'LEI0001', 'source_url': 'https://api.gleif.org/api/v1/lei-records/LEI0001', 'checked_at': TODAY},
           'listing': {'ticker': 'LPW', 'exchange': 'LSE', 'source_url': 'https://example.org/listing', 'checked_at': TODAY},
           'link': [{'url': 'https://example.org/annual-report', 'proves': 'Listed Power owns 50% of Fixture wind farm', 'retrieved_at': TODAY}],
           'reviewer': 'test', 'verified_at': TODAY}
    rec.update(kw)
    return rec


class InvestLayer(unittest.TestCase):
    def setUp(self):
        self.reg = Registry(ENTITIES, EDGES)

    def run_build(self, rows, ledger=None):
        return build(rows, ISO, self.reg, ledger or {}, TODAY)

    def test_owner_split_keeps_stakes_and_ids(self):
        owners = split_owners('A Co [65.0%]; B Co [35.0%]; unknown', 'E1 [65.0%]; E2 [35.0%]; E9')
        self.assertEqual([(o['name'], o['entity_id'], o['stake']) for o in owners], [('A Co', 'E1', 65.0), ('B Co', 'E2', 35.0)])
        self.assertIsNone(split_owners('A Co', None)[0]['stake'])

    def test_unverified_candidate_is_never_public(self):
        research, report, export = self.run_build([unit()])
        self.assertEqual(research[0]['candidate_exposures'][0]['type'], 'E1')
        self.assertEqual((report['public_projects'], export['projects']), (0, []))
        self.assertIn('no verified exposure to a listed company', research[0]['reasons'])

    def test_verified_owner_goes_public_with_evidence_and_other_owners(self):
        _, report, export = self.run_build([unit()], {'gem:L1|E1': record()})
        p = export['projects'][0]
        self.assertEqual((report['public_projects'], p['cc'], p['cost'], p['progress']), (1, 'GB', None, None))
        self.assertEqual(p['exposures'][0]['verification']['listing']['ticker'], 'LPW')
        self.assertEqual([o['name'] for o in p['other_owners']], ['State Utility'])

    def test_name_or_ticker_match_alone_is_not_enough(self):
        # No GEM ID, and the name is not an exact registry name: Samsung C&T Renewables must not become Samsung Electronics.
        research, _, _ = self.run_build([unit(**{'Owner(s)': 'Samsung C&T Renewables, LLC', 'Owner(s) GEM Entity ID': None})])
        self.assertEqual(research[0]['candidate_exposures'], [])
        # Ambiguous exact name (two registry entities) is not matched either.
        self.assertEqual(self.reg.exposures({'name': 'Twin', 'entity_id': None, 'stake': None}), [])
        # An exact unique name is only a candidate, flagged as a name match.
        self.assertEqual(self.reg.exposures({'name': 'Samsung C&T Corp', 'entity_id': None, 'stake': None})[0]['owner_match'], 'name')

    def test_parent_chain_needs_every_link_documented(self):
        rows = [unit(**{'Owner(s)': 'Project Holdco LLC [100%]', 'Owner(s) GEM Entity ID': 'E2 [100%]'})]
        research, _, _ = self.run_build(rows)
        e = research[0]['candidate_exposures'][0]
        self.assertEqual((e['type'], e['path'], e['effective_stake']), ('E3', ['E2', 'E1'], 60.0))
        self.assertEqual(self.run_build(rows, {'gem:L1|E1': record()})[1]['public_projects'], 0)
        linked = record(link=[{'url': 'https://example.org/annual-report', 'proves': 'Holdco is 60% owned by Listed Power', 'retrieved_at': TODAY, 'edge': ['E2', 'E1']}])
        self.assertEqual(self.run_build(rows, {'gem:L1|E1': linked})[1]['public_projects'], 1)

    def test_owner_ids_pair_by_name_not_position(self):
        # GEM row with names and IDs in different orders (real case: Rabigh 2).
        rows = [unit(**{'Owner(s)': 'State Utility [50%]; Listed Power PLC [50%]', 'Owner(s) GEM Entity ID': 'E1 [50%]; E3 [50%]'})]
        research, _, _ = self.run_build(rows)
        self.assertEqual([(e['owner'], e['listed_entity_id']) for e in research[0]['candidate_exposures']], [('Listed Power PLC', 'E1')])
        self.assertEqual({o['name']: o['entity_id'] for o in research[0]['owners']}, {'State Utility': 'E3', 'Listed Power PLC': 'E1'})

    def test_unknown_stake_stays_unknown(self):
        e = self.reg.exposures({'name': 'Project Holdco', 'entity_id': 'E2', 'stake': None})[0]
        self.assertIsNone(e['effective_stake'])

    def test_aggregator_only_evidence_and_expiry_fail(self):
        exp = {'type': 'E1', 'path_edges': [], 'sector': 'Energy & Utilities'}
        gem_only = record(link=[{'url': 'https://www.gem.wiki/Fixture', 'proves': 'x', 'retrieved_at': TODAY}])
        self.assertIn('no primary document for the project-to-company link', exposure_problems(exp, gem_only, TODAY))
        self.assertIn('verification expired', exposure_problems(exp, record(verified_at='2026-01-01'), TODAY))
        self.assertEqual(exposure_problems(exp, record(), TODAY), [])
        self.assertTrue(exposure_problems(dict(exp, type='E5'), record(), TODAY))
        self.assertTrue(exposure_problems(dict(exp, type='E4'), record(), TODAY))

    def test_cancelled_or_unlocated_projects_drop_out(self):
        self.assertEqual(self.run_build([unit(Status='cancelled')])[1]['pipeline_projects'], 0)
        ok, reasons, _ = evaluate({'id': 'x', 'stage': 'Under construction', 'precision': None, 'lat': 1, 'lon': 1, 'cc': 'GB', 'source': {'licence': 'CC BY 4.0'}}, [], {}, TODAY)
        self.assertFalse(ok)
        self.assertIn('no usable location', reasons)

    def test_every_country_gets_an_iso_code(self):
        research, report, _ = self.run_build([unit(**{'Country/area': 'United States', 'GEM location ID': 'L2'})])
        self.assertEqual((research[0]['cc'], report['missing_country_code']), ('US', 0))

    def test_research_only_fields_never_reach_the_public_file(self):
        _, _, export = self.run_build([unit()], {'gem:L1|E1': record()})
        self.assertFalse({'candidate_exposures', 'reasons', 'owners'} & set(export['projects'][0]))


if __name__ == '__main__':
    unittest.main()
