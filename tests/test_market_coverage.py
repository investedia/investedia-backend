import importlib.util,unittest
from pathlib import Path
from datetime import date,timedelta
s=importlib.util.spec_from_file_location('market',Path(__file__).resolve().parents[1]/'tools/coverage/market_data.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class MarketTests(unittest.TestCase):
 def test_fx_quote_direction_and_dates(self):
  out=m.ecb_rates('<Envelope><Cube time="2026-11-09"><Cube currency="USD" rate="1.25"/><Cube currency="JPY" rate="150"/></Cube></Envelope>')
  self.assertEqual(out['USDJPY'],[{'date':'2026-11-09','close':120}]);self.assertEqual(out['USDEUR'][0]['close'],.8)
 def series(self):
  # Clearly synthetic mathematical fixture, never written as market data.
  return [{'date':(date(2026,9,1)+timedelta(days=i)).isoformat(),'close':100+i+i*i/100} for i in range(31)]
 def test_thirty_returns_not_thirty_prices_and_flat_is_not_correlated(self):
  rows=self.series();self.assertIsNone(m.correlation(rows[:30],rows));self.assertAlmostEqual(m.correlation(rows,rows)['correlation'],1)
  flat=[dict(x,close=100) for x in rows];self.assertIsNone(m.correlation(rows,flat))
  with self.assertRaises(ValueError):m.correlation(rows+[rows[0]],rows)
 def test_missing_intermediate_day_is_not_a_daily_return(self):
  rows=self.series();a=rows+[{'date':'2026-10-02','close':140}]
  b=a[:10]+a[11:];self.assertIsNone(m.correlation(a,b))
 def test_no_licence_no_correlation_or_exchange_move(self):
  self.assertEqual(m.exchange_connections({'XAAA':{}},{'XAAA':{'prices':self.series()}})['exchanges'],{})
if __name__=='__main__':unittest.main()
