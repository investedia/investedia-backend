# Markets coverage preparation

Not investment advice.

The audit finds no exchange trading-hour sessions/time zones in the 63-row
exchange snapshot, no verified 10-year yield quote coverage, and no sourced
ranking proving the listed issuers are each country's largest companies.
Existing legacy index/FX/company prices are honestly dated but their Yahoo
redistribution rights are not established. They were not scraped or refreshed.

The ECB historical reference-rate adapter prepares **staging-only** currencies
per USD with each original daily observation date. These are official reference
rates, not executable prices. Its reuse notice and XML endpoint were blocked by
the environment allowlist. No new FX quote was published and no licence is
claimed verified. Index/bond prices remain empty instead of using proxies.

There is no cleared free source yet for all missing indices/bond yields. FRED
is a distributor, not a blanket licence for every upstream series; no FRED key
or Yahoo workaround was introduced. Official exchange sessions must be checked
against the exchange's primary source, including holidays/lunch breaks and its
IANA time zone. No generic 09:00–17:00 hours were guessed into exchanges.json.
Those gaps remain documented, not presented as completed coverage.

`exchange-correlations.json` is the requested separate, UI-free output: daily
moves and pairs with Pearson correlation >= 0.6 across 30 aligned daily returns
(require 31 dated closes and source/licence metadata). Undated 22-point
sparklines cannot supply that evidence. No dated licensed exchange benchmark
series is available, so it currently reports 63 missing exchanges and zero
moves/pairs. FX reference rates are never substituted for stock-index closes.

Run `python tools/coverage/market_data.py --fetch` after network access is fixed.
For reviewed dated benchmark inputs, add `--series PATH`: keys are MIC codes;
each value has `source_url`, `licence_url`, `redistribution_allowed` and `prices`
with ISO-date/close observations. Tests use explicitly synthetic arithmetic
fixtures only, never persisted as real market data. The saved quote files,
exchange coordinates, financial ledgers and production price pipeline remain
unchanged until source/terms verification can be completed.

Cost: 0 Gemini calls, no schedule, no paid service, no new secret. Added hourly
Actions/Gemini consumption: zero. Full source integration remains blocked on
licensing and reachability; this branch provides safe adapters and diagnostics.

## Follow-up: licensed exchange calendars available

The Python package registry was reachable even though direct official sites were
blocked. `exchange-calendars` 4.13.2 is Apache-2.0; its full licence is retained
in `third-party/exchange-calendars-LICENSE.txt`. The importer applies only MICs
explicitly supported by the library (including its documented aliases), never
a guessed country-wide timetable. See `exchange-hours-report.json` for updated
and unsupported venues. `data/exchanges.json` now includes local regular hours,
IANA zones, breaks, day offsets, and dated sessions for 10 Nov–12 Dec 2026,
including known holidays/early closes. These are library-maintained calendars,
not a guarantee against emergency exchange closures. Outside the dated horizon
only regular hours are known. No UI or production system was switched over.

Optional reproducible import: install `tools/coverage/requirements-calendars.txt`
in a local venv, then run `python tools/coverage/exchange_hours.py --as-of YYYY-MM-DD`.
Regular tests do not require that dependency. This is source-attributed factual
calendar metadata; it does not clear any quote licence or fill missing prices.
