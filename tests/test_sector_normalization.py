import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("sector",ROOT/"tools/sector_normalization.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SectorTests(unittest.TestCase):
    def test_verified_real_sec_records(self):
        rows=json.loads((ROOT/"assets/globe/industries.json").read_text())["by"]
        for ticker, expected in [("AMD","Information technology"),("AMAL","Financials"),("ABBV","Health care")]:
            r=rows[ticker];self.assertEqual(m.normalize_sector(r["industry"],r["sic"])["sector"],expected)
    def test_unknown_and_ambiguous_preserve_raw(self):
        for raw in ("Unclassified infrastructure", "Coal", "Mixed holdings"):
            self.assertEqual(m.normalize_sector(raw,"9999"),{"sector":None,"raw":raw,"basis":None})
    def test_controlled_taxonomy_and_no_range_inference(self):
        self.assertEqual(len(m.SECTORS), 11)
        self.assertTrue(set(m.TAXONOMY['sic'].values()) <= set(m.SECTORS))
        self.assertTrue(set(m.TAXONOMY['aliases'].values()) <= set(m.SECTORS))
        self.assertIsNone(m.normalize_sector('Unknown', '6001')['sector'])
        self.assertEqual(m.normalize_sector('Banking', '6798')['sector'], 'Real estate')
        self.assertEqual(m.normalize_sector(None)['raw'], None)
    def test_real_records_across_sectors(self):
        rows=json.loads((ROOT/'assets/globe/industries.json').read_text())['by']
        for ticker, expected in [('XOM','Energy'),('BHP','Materials'),('CAT','Industrials'),('KO','Consumer staples'),('F','Consumer discretionary'),('T','Communication services'),('AMT','Real estate')]:
            row=rows[ticker];before=dict(row)
            result=m.normalize_sector(row['industry'],row['sic'])
            self.assertEqual(result['sector'],expected)
            self.assertEqual(result['raw'],row['industry']);self.assertEqual(row,before)
    def test_aliases_and_invalid_sic(self):
        self.assertEqual(m.normalize_sector(" Banking ","602x")["sector"],"Financials")
        self.assertIsNone(m.normalize_sector("Unknown",6022)["sector"])
