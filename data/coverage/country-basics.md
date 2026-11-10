# Country basics: preserved observations and gated refresh

Not investment advice.

`data/country-basics.json` contains 224 mapped ISO country/territory records.
It preserves **990 existing numeric observations**, without re-dating them,
from the saved World Bank WDI snapshot (CC BY 4.0). Each numeric observation has
its indicator, value, units, original observation year, source URL, licence and
original snapshot retrieval time. The legacy `gdp`, `growth`, `infl`, `unemp`,
`pop` array shapes are retained for compatibility with existing country panels.
The file is additional prepared data; no frontend consumer or live API was
switched to it, and no public snapshot was overwritten.

A seven-indicator World Bank API refresh was attempted. All seven requests were
blocked by this environment's allowlist. Original data are explicitly marked
`saved_snapshot_not_reverified`; no fresh reading is claimed. Three existing
GeoNames currency identifiers retain their CC BY 4.0 attribution. Unsourced
policy rates, central bank names, credit ratings and next meeting dates remain
null. The 16 globe shapes lacking ISO mappings are listed separately rather
than assigned guessed national statistics.

GDP/growth/inflation/unemployment/population use existing WDI observations.
The adapter also supports central-government debt (% GDP, **not general
 government debt**) and current-account balance (% GDP) where WDI reports them.
Annual CPI change is not relabelled as the latest monthly y/y release. A source
that returns null, an aggregate, an undated/invalid value or a future year does
not fill a gap. Pagination cannot silently truncate an API response.

The proposed weekly workflow is disabled unless repository variable
`COUNTRY_BASICS_ENABLED=true` is separately enabled on main. It has a five-minute
timeout, read-only repository permission, concurrency limit and visible failure.
It saves a review artifact; it does not commit, deploy or overwrite live data.
The owner/Claude must approve how reviewed snapshots reach the site. No secret
is required. No new source value is published without review.

Requests use `User-Agent: InvestediaRobot/1.0`. The normal batch is seven WDI
requests (global results filtered to existing ISO mappings), no Gemini calls.
Added hourly news runtime, Actions minutes and Gemini calls are **zero**. The
weekly refresh is currently off; its configured ceiling is five minutes/week
(up to about 25 minutes/month), actual hosted timing must be measured after
network access is approved. No paid service is added.
