"""Add real companies to the asset universe (the inline /*MK*/ list in assets/globe/index.html), checking each symbol
against Yahoo first. Run: python3 tools/add-companies.py && python3 update_globe.py && python3 tools/gen-worker-symbols.py && python3 build.py"""
import json, re, urllib.request, urllib.parse, concurrent.futures as cf
PAGE = 'assets/globe/index.html'
NA, EU, AS = 'North America', 'Europe', 'Asia'
# symbol, name, group, country, city, lat, lon, region, cc
R = [
 ('PLD','Prologis','Real Estate','United States','San Francisco',37.77,-122.42,NA,'us'),('AMT','American Tower','Real Estate','United States','Boston',42.36,-71.06,NA,'us'),
 ('EQIX','Equinix','Real Estate','United States','Redwood City',37.49,-122.24,NA,'us'),('WELL','Welltower','Real Estate','United States','Toledo',41.65,-83.54,NA,'us'),
 ('SPG','Simon Property Group','Real Estate','United States','Indianapolis',39.77,-86.16,NA,'us'),('PSA','Public Storage','Real Estate','United States','Glendale',34.14,-118.26,NA,'us'),
 ('O','Realty Income','Real Estate','United States','San Diego',32.72,-117.16,NA,'us'),('DLR','Digital Realty','Real Estate','United States','Austin',30.27,-97.74,NA,'us'),
 ('CCI','Crown Castle','Real Estate','United States','Houston',29.76,-95.37,NA,'us'),('VICI','VICI Properties','Real Estate','United States','New York',40.71,-74.0,NA,'us'),
 ('AVB','AvalonBay Communities','Real Estate','United States','Arlington',38.88,-77.1,NA,'us'),('EQR','Equity Residential','Real Estate','United States','Chicago',41.88,-87.63,NA,'us'),
 ('DUK','Duke Energy','Utilities','United States','Charlotte',35.23,-80.84,NA,'us'),('SO','Southern Company','Utilities','United States','Atlanta',33.75,-84.39,NA,'us'),
 ('D','Dominion Energy','Utilities','United States','Richmond',37.54,-77.43,NA,'us'),('AEP','American Electric Power','Utilities','United States','Columbus',39.96,-83.0,NA,'us'),
 ('EXC','Exelon','Utilities','United States','Chicago',41.88,-87.63,NA,'us'),('SRE','Sempra','Utilities','United States','San Diego',32.72,-117.16,NA,'us'),
 ('XEL','Xcel Energy','Utilities','United States','Minneapolis',44.98,-93.27,NA,'us'),('ED','Consolidated Edison','Utilities','United States','New York',40.71,-74.0,NA,'us'),
 ('NGG','National Grid','Utilities','United Kingdom','London',51.51,-0.13,EU,'gb'),('PEG','Public Service Enterprise Group','Utilities','United States','Newark',40.74,-74.17,NA,'us'),
 ('WEC','WEC Energy Group','Utilities','United States','Milwaukee',43.04,-87.91,NA,'us'),
 ('BRK-B','Berkshire Hathaway','Finance','United States','Omaha',41.26,-95.93,NA,'us'),('CB','Chubb','Finance','Switzerland','Zurich',47.37,8.54,EU,'ch'),
 ('PGR','Progressive','Finance','United States','Mayfield Village',41.55,-81.44,NA,'us'),('AIG','American International Group','Finance','United States','New York',40.71,-74.0,NA,'us'),
 ('MET','MetLife','Finance','United States','New York',40.71,-74.0,NA,'us'),('PRU','Prudential Financial','Finance','United States','Newark',40.74,-74.17,NA,'us'),
 ('ALL','Allstate','Finance','United States','Northbrook',42.13,-87.83,NA,'us'),('TRV','Travelers','Finance','United States','New York',40.71,-74.0,NA,'us'),
 ('AFL','Aflac','Finance','United States','Columbus',32.46,-84.99,NA,'us'),('HIG','The Hartford','Finance','United States','Hartford',41.76,-72.67,NA,'us'),
 ('AXAHY','AXA','Finance','France','Paris',48.86,2.35,EU,'fr'),('ZURVY','Zurich Insurance','Finance','Switzerland','Zurich',47.37,8.54,EU,'ch'),
 ('GM','General Motors','Consumer','United States','Detroit',42.33,-83.05,NA,'us'),('F','Ford Motor','Consumer','United States','Dearborn',42.32,-83.18,NA,'us'),
 ('STLA','Stellantis','Consumer','Netherlands','Amsterdam',52.37,4.9,EU,'nl'),('RACE','Ferrari','Consumer','Italy','Maranello',44.53,10.86,EU,'it'),
 ('HMC','Honda Motor','Consumer','Japan','Tokyo',35.68,139.69,AS,'jp'),('VWAGY','Volkswagen','Consumer','Germany','Wolfsburg',52.42,10.79,EU,'de'),
 ('BMWYY','BMW','Consumer','Germany','Munich',48.14,11.58,EU,'de'),('MBGYY','Mercedes-Benz Group','Consumer','Germany','Stuttgart',48.78,9.18,EU,'de'),
 ('POAHY','Porsche','Consumer','Germany','Stuttgart',48.78,9.18,EU,'de'),('RIVN','Rivian Automotive','Consumer','United States','Irvine',33.68,-117.83,NA,'us'),
 ('LCID','Lucid Group','Consumer','United States','Newark',37.53,-122.04,NA,'us'),('NIO','NIO','Consumer','China','Shanghai',31.23,121.47,AS,'cn'),
 ('XPEV','XPeng','Consumer','China','Guangzhou',23.13,113.26,AS,'cn'),('LI','Li Auto','Consumer','China','Beijing',39.9,116.4,AS,'cn'),('BYDDY','BYD','Consumer','China','Shenzhen',22.54,114.06,AS,'cn'),
 ('LMT','Lockheed Martin','Industrials','United States','Bethesda',38.98,-77.1,NA,'us'),('RTX','RTX','Industrials','United States','Arlington',38.88,-77.1,NA,'us'),
 ('NOC','Northrop Grumman','Industrials','United States','Falls Church',38.88,-77.17,NA,'us'),('GD','General Dynamics','Industrials','United States','Reston',38.96,-77.34,NA,'us'),
 ('LHX','L3Harris','Industrials','United States','Melbourne',28.08,-80.61,NA,'us'),('HII','Huntington Ingalls','Industrials','United States','Newport News',36.98,-76.43,NA,'us'),
 ('TDG','TransDigm','Industrials','United States','Cleveland',41.5,-81.69,NA,'us'),('RNMBY','Rheinmetall','Industrials','Germany','Dusseldorf',51.23,6.78,EU,'de'),
 ('BAESY','BAE Systems','Industrials','United Kingdom','London',51.51,-0.13,EU,'gb'),('SAFRY','Safran','Industrials','France','Paris',48.86,2.35,EU,'fr'),('THLLY','Thales','Industrials','France','Paris',48.86,2.35,EU,'fr'),
 ('CAT','Caterpillar','Industrials','United States','Irving',32.81,-96.95,NA,'us'),('DE','Deere & Company','Industrials','United States','Moline',41.51,-90.51,NA,'us'),
 ('HON','Honeywell','Industrials','United States','Charlotte',35.23,-80.84,NA,'us'),('GE','GE Aerospace','Industrials','United States','Boston',42.36,-71.06,NA,'us'),
 ('UPS','United Parcel Service','Industrials','United States','Atlanta',33.75,-84.39,NA,'us'),('MMM','3M','Industrials','United States','Saint Paul',44.95,-93.09,NA,'us'),
 ('UNP','Union Pacific','Industrials','United States','Omaha',41.26,-95.93,NA,'us'),('ETN','Eaton','Industrials','Ireland','Dublin',53.35,-6.26,EU,'ie'),
 ('EMR','Emerson Electric','Industrials','United States','St. Louis',38.63,-90.2,NA,'us'),('FDX','FedEx','Industrials','United States','Memphis',35.15,-90.05,NA,'us'),
 ('SLB','SLB','Energy','United States','Houston',29.76,-95.37,NA,'us'),('COP','ConocoPhillips','Energy','United States','Houston',29.76,-95.37,NA,'us'),('EOG','EOG Resources','Energy','United States','Houston',29.76,-95.37,NA,'us'),('OXY','Occidental Petroleum','Energy','United States','Houston',29.76,-95.37,NA,'us'),
 ('MRK','Merck & Co.','Healthcare','United States','Rahway',40.61,-74.28,NA,'us'),('ABBV','AbbVie','Healthcare','United States','North Chicago',42.33,-87.84,NA,'us'),('TMO','Thermo Fisher Scientific','Healthcare','United States','Waltham',42.38,-71.24,NA,'us'),('ABT','Abbott Laboratories','Healthcare','United States','Abbott Park',42.29,-87.9,NA,'us'),
 ('LIN','Linde','Materials','United Kingdom','London',51.51,-0.13,EU,'gb'),('SHW','Sherwin-Williams','Materials','United States','Cleveland',41.5,-81.69,NA,'us'),('FCX','Freeport-McMoRan','Materials','United States','Phoenix',33.45,-112.07,NA,'us'),('NEM','Newmont','Materials','United States','Denver',39.74,-104.99,NA,'us'),('DOW','Dow','Materials','United States','Midland',43.62,-84.25,NA,'us'),
 ('MU','Micron Technology','Technology','United States','Boise',43.62,-116.2,NA,'us'),('QCOM','Qualcomm','Technology','United States','San Diego',32.72,-117.16,NA,'us'),('TXN','Texas Instruments','Technology','United States','Dallas',32.78,-96.8,NA,'us'),
 ('AMAT','Applied Materials','Technology','United States','Santa Clara',37.35,-121.95,NA,'us'),('LRCX','Lam Research','Technology','United States','Fremont',37.55,-121.99,NA,'us'),('KLAC','KLA','Technology','United States','Milpitas',37.43,-121.9,NA,'us'),
 ('MRVL','Marvell Technology','Technology','United States','Wilmington',39.74,-75.55,NA,'us'),('ARM','Arm Holdings','Technology','United Kingdom','Cambridge',52.2,0.12,EU,'gb'),('ON','ON Semiconductor','Technology','United States','Scottsdale',33.49,-111.93,NA,'us'),
 ('ADI','Analog Devices','Technology','United States','Wilmington',42.55,-71.17,NA,'us'),('NXPI','NXP Semiconductors','Technology','Netherlands','Eindhoven',51.44,5.48,EU,'nl'),('MCHP','Microchip Technology','Technology','United States','Chandler',33.3,-111.84,NA,'us'),('STM','STMicroelectronics','Technology','Switzerland','Geneva',46.2,6.14,EU,'ch'),
 ('AVB','AvalonBay Communities','Real Estate','United States','Arlington',38.88,-77.1,NA,'us'),('EQR','Equity Residential','Real Estate','United States','Chicago',41.88,-87.63,NA,'us'),('BMWYY','BMW','Consumer','Germany','Munich',48.14,11.58,EU,'de'),
]
html = open(PAGE, encoding='utf-8').read()
mk = json.loads(re.search(r'/\*MK\*/(.*?)/\*MK\*/', html, re.S).group(1)); have = {m['s'] for m in mk}
def ok(r):
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1mo&interval=1d' % urllib.parse.quote(r[0]), headers={'User-Agent': 'Mozilla/5.0'}), timeout=20))
        c = [x for x in j['chart']['result'][0]['indicators']['quote'][0]['close'] if x is not None]
        return len(c) >= 6
    except Exception:
        return False
new = [r for r in R if r[0] not in have]
with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(ok, new))
added = []
for r, good in zip(new, res):
    if not good: print('skip (no Yahoo data):', r[0]); continue
    mk.append({'s': r[0], 't': 'stocks', 'g': r[2], 'n': r[1], 'k': r[3], 'c': r[4], 'la': r[5], 'lo': r[6], 'r': r[7], 'm': 0, 'p': 0, 'd': 0, 'w': 0, 'site': r[0], 'cc': r[8]}); added.append(r[0])
data = json.dumps(mk, separators=(',', ':'), ensure_ascii=False)
html = re.sub(r'/\*MK\*/.*?/\*MK\*/', lambda _: '/*MK*/' + data + '/*MK*/', html, count=1, flags=re.S)
open(PAGE, 'w', encoding='utf-8').write(html); print('added', len(added), ':', ' '.join(added))
