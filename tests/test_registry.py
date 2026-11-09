"""Canonical registry: identity rules and the committed data/registry.json. Offline."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import registry as R, events as E

REG = R.Registry()

def rid(name, ticker=None, kind='company'):
    return REG.resolve(name, ticker, kind)['id']

class Identity(unittest.TestCase):
    def test_same_concept_fx(self):
        for t in ('BRL=X', 'USDBRL', 'USDBRL=X', 'USD/BRL', 'BRLUSD=X'):
            self.assertEqual(rid('Brazilian real', t, 'asset'), 'FX:USDBRL', t)
        self.assertEqual(rid('Brazilian Real', None, 'asset'), 'FX:USDBRL')
        self.assertEqual(rid('Euro', 'EUR=X', 'asset'), 'FX:EURUSD')

    def test_site_code_is_not_a_ticker(self):
        self.assertEqual(rid('LVMH', 'MC'), 'EQ:XPAR:MC')
        self.assertEqual(rid('Moelis & Company', 'MC'), 'EQ:XNYS:MC')
        self.assertEqual(rid('Airbus', 'AIR'), 'EQ:XPAR:AIR')
        self.assertIsNone(rid('Someone Else Entirely', 'MC'))

    def test_wrong_ticker_never_guessed(self):
        r = REG.resolve('Totally Unknown Widgets', 'ZZZZQ', 'company')
        self.assertIsNone(r['id']); self.assertIn('unknown', r['reason'])
        r = REG.resolve('Banco Bradesco', 'AAPL', 'company')  # a ticker that belongs to another company is not trusted
        self.assertNotEqual(r['id'], REG.ids_for_ticker('AAPL')[0])

    def test_sectors_and_countries_are_not_assets(self):
        self.assertIsNone(rid('Semiconductors', 'SMH', 'sector'))
        self.assertIsNone(rid('Brazil', '^BVSP', 'country'))

    def test_fixed_assets(self):
        self.assertEqual(rid('Bitcoin', 'BTC-USD', 'asset'), 'CR:BTC')
        self.assertEqual(rid('Bitcoin', None, 'asset'), 'CR:BTC')
        self.assertEqual(rid('Ethereum', 'ETH', 'asset'), 'CR:ETH')
        self.assertEqual(rid('10-Year Treasury Yield', '^TNX', 'asset'), 'RT:US10Y')
        self.assertEqual(rid('US 10-year Treasury yield', None, 'asset'), 'RT:US10Y')
        self.assertEqual(rid('Brent crude', None, 'asset'), 'CM:BRENT')
        self.assertEqual(rid('Gold', 'GC=F', 'asset'), 'CM:XAU')
        self.assertEqual(rid('S&P 500', '^GSPC', 'asset'), 'IX:SPX')
        self.assertIsNone(rid('Oil', None, 'asset'))  # Brent or WTI: not guessed

    def test_drawable_assets_have_places(self):
        for aid in ('RT:US10Y', 'RT:US02Y', 'FX:USDBRL', 'IX:SPX', 'EQ:XPAR:MC'):
            self.assertTrue(REG.drawable(aid), aid)

    def test_crypto_is_verified_but_has_no_place(self):
        for aid in [a for a in REG.assets if a.startswith('CR:')]:
            self.assertTrue(REG.verified(aid)); self.assertFalse(REG.drawable(aid), aid)  # no artificial hub: no Globe line
        row = R.stamp({'kind': 'asset', 'name': 'Bitcoin', 'ticker': 'BTC-USD', 'direction': 'up'})
        self.assertEqual(row['asset']['id'], 'CR:BTC'); self.assertEqual(row['asset']['px'], 'BTC-USD')  # still priced
        self.assertNotIn('la', row['asset'])
        import update_news_track as T  # still eligible for the Live Track Record
        self.assertEqual(T.resolve_row(row, {'BTC-USD'}), 'BTC-USD')

    def test_known_collisions(self):
        cases = {('LVMH', 'MC'): 'EQ:XPAR:MC', ('Airbus', 'AIR'): 'EQ:XPAR:AIR', ('Allianz', 'ALV'): 'EQ:XETR:ALV', ("L'Oréal", 'OR'): 'EQ:XPAR:OR',
                 ('Roche', 'ROG'): 'EQ:XSWX:RO', ('CSL', 'CSL'): 'EQ:XASX:CSL', ('Wesfarmers', 'WES'): 'EQ:XASX:WES', ('MTN Group', 'MTN'): 'EQ:XJSE:MTN',
                 ('Fisher & Paykel Healthcare', 'FPH'): 'EQ:XNZE:FPH', ('Saudi Telecom', 'STC'): 'EQ:XSAU:7010',
                 ('Moelis & Company', 'MC'): 'EQ:XNYS:MC', ('AAR Corp', 'AIR'): 'EQ:XNYS:AIR', ('Autoliv', 'ALV'): 'EQ:XNYS:ALV', ('Carlisle Companies', 'CSL'): 'EQ:XNYS:CSL',
                 ('Vail Resorts', 'MTN'): 'EQ:XNYS:MTN'}
        for (name, t), want in cases.items():
            self.assertEqual(rid(name, t), want, (name, t))
        import update_globe as G  # Globe prices come from the intended listing, not the US letters
        for g, y in {'MC': 'MC.PA', 'AIR': 'AIR.PA', 'ALV': 'ALV.DE', 'OR': 'OR.PA', 'ROG': 'RO.SW', 'CSL': 'CSL.AX', 'WES': 'WES.AX', 'MTN': 'MTN.JO', 'FPH': 'FPH.NZ', 'STC': '7010.SR'}.items():
            self.assertEqual(G.ysym({'s': g, 't': 'stocks'}), y, g)

    def test_company_links_listings(self):
        a, b = REG.assets['EQ:XNYS:TM'], REG.assets['EQ:XTKS:7203']
        self.assertEqual(a['company'], b['company'])
        self.assertEqual(rid('Toyota Motor', 'TM'), 'EQ:XNYS:TM')  # a ticker names that exact listing
        self.assertEqual(rid('Toyota', None), 'EQ:XTKS:7203')  # a bare company name: the home listing represents the company

    def test_name_matcher(self):
        self.assertTrue(R.same_company('Eli Lilly', 'ELI LILLY & Co'))
        self.assertTrue(R.same_company('IBM', 'International Business Machines Corp'))
        self.assertTrue(R.same_company('BP', 'BP p.l.c.'))
        self.assertFalse(R.same_company('Deutsche Bank', 'Deutsche Telekom AG'))
        self.assertFalse(R.same_company('Banco do Brasil', 'Banco Bradesco SA'))
        self.assertFalse(R.same_company('LVMH', 'Moelis & Co'))

    def test_stamp(self):
        row = R.stamp({'kind': 'company', 'name': 'LVMH', 'ticker': 'MC'})
        self.assertEqual(row['asset']['id'], 'EQ:XPAR:MC'); self.assertEqual(row['asset']['px'], 'MC.PA')
        row = R.stamp({'kind': 'sector', 'name': 'Luxury', 'ticker': None})
        self.assertNotIn('asset', row); self.assertTrue(row['unresolved'])

    def test_registry_file(self):
        self.assertGreater(len(REG.assets), 1000)
        for aid, a in REG.assets.items():
            self.assertEqual(aid, a['id'])
            self.assertTrue(a.get('verify'), aid)
        for t, ids in REG.alias.items():
            for i in ids: self.assertIn(i, REG.assets, t)

class Threads(unittest.TestCase):
    def ev(self, i, at, aid, fam='earnings', cluster=None):
        return {'id': i, 'at': at, 'fam': fam, 'cluster': cluster or i, 'assets': [{'id': aid}]}

    def test_rules(self):
        evs = [self.ev('a', '2026-10-01T00:00:00Z', 'X'), self.ev('b', '2026-10-01T00:30:00Z', 'X'),  # 30 min: too close
               self.ev('c', '2026-10-02T00:00:00Z', 'X'), self.ev('d', '2026-10-09T00:00:00Z', 'X'),  # 7 days: too far
               self.ev('e', '2026-10-02T05:00:00Z', 'X', fam='m&a'), self.ev('f', '2026-10-02T06:00:00Z', 'Y')]
        self.assertEqual(E.threads(evs), [('b', 'c', 'X')])

if __name__ == '__main__': unittest.main()
