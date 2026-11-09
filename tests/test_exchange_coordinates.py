"""Exchange geography must be attributable and must never guess across countries."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/registry/exchange_coordinates.py'
if not SOURCE.is_file():
    raise unittest.SkipTest(
        'Recovered backend lacks tools/registry/exchange_coordinates.py; '
        'restore the original tool and source metadata from the owner archive before running geography tests.'
    )
spec = importlib.util.spec_from_file_location('exchange_coordinates', SOURCE)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)


class ExchangeCoordinatesTest(unittest.TestCase):
    def record(self, country='NG', city='Lagos'):
        row = [''] * 19
        row[0:9] = ['2332459', city, city, city, '6.45407', '3.39467', 'P', 'PPLA', country]
        return row

    def test_all_exchange_markers_have_attributed_city_positions(self):
        exchanges = json.loads(geo.DATA.read_text())
        ids = json.loads(geo.CITY_IDS.read_text())
        self.assertEqual(set(exchanges), set(ids))
        for mic, exchange in exchanges.items():
            with self.subTest(mic=mic):
                pos = exchange['coordinates']
                self.assertEqual(pos['source'], f'https://www.geonames.org/{ids[mic]}')
                self.assertEqual(pos['precision'], 'city')
                self.assertEqual(pos['attribution'], 'GeoNames · CC BY 4.0')
                self.assertTrue(-90 <= pos['latitude'] <= 90)
                self.assertTrue(-180 <= pos['longitude'] <= 180)
        self.assertEqual(ids['XNSA'], 2332459)  # Lagos, Nigeria
        self.assertEqual(ids['XKLS'], 1735161)  # Kuala Lumpur, Malaysia
        self.assertEqual(ids['XETR'], 2925533)  # Frankfurt am Main, not Oder
        self.assertEqual(ids['XHKG'], 1819729)  # City, not Hong Kong Island

    def test_country_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            geo.verify_source({'country': 'NG', 'city': 'Lagos'}, self.record('PT'))

    def test_city_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            geo.verify_source({'country': 'NG', 'city': 'Abuja'}, self.record())

    def test_invalid_coordinates_rejected(self):
        row = self.record()
        row[4] = 'nan'
        with self.assertRaises(ValueError):
            geo.verify_source({'country': 'NG', 'city': 'Lagos'}, row)

    def test_city_alias_accepted_without_fuzzy_matching(self):
        row = self.record('US', 'New York City')
        row[3] = 'New York,NYC'
        result = geo.verify_source({'country': 'US', 'city': 'New York'}, row)
        self.assertEqual(result['precision'], 'city')
        with self.assertRaises(ValueError):
            geo.verify_source({'country': 'US', 'city': 'York'}, row)


if __name__ == '__main__':
    unittest.main()
