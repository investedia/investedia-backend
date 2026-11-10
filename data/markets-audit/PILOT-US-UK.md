# US / UK Markets pilot — artifact and API code only

Not investment advice.

Owner decisions, 10 November 2026, supersede the phase-01 pending-source scope:
Wikidata structured data (CC0), GLEIF LEI/Level 2 (CC0), SEC EDGAR identifiers and
numerical XBRL facts, World Bank WDI (CC BY 4.0), ECB reference rates, and retained
exchange-calendars sessions are approved. No Nasdaq Trader, JSE, NGX, B3 or NSE
India listing files are fetched or used. No existing price registry seeds this
pilot. No issuer-authored report prose, images or authenticated APIs are copied.

## Current result and limits

No primary-source collection or Actions dispatch was performed in the sandbox.
**Actual verified counts, denominator, coverage, conflicts, FX relationships,
measured runtime and production artifact size are pending the manual runner.**
`pilot-status.json` makes these unknowns machine-readable. No country is proposed
for launch before those observations. Offline synthetic fixture counts are test
assertions, not a market inventory; fixture artifacts cannot be published.

US: denominator = distinct CIKs in SEC's paired
`company_tickers_exchange.json` rows on XNYS / XNAS / XASE. This SEC file is NOT
the unapproved Nasdaq Trader directory. Each filer must have a submissions
record. Active status requires the directory ticker still present in submissions.
Explicit Wikidata share/security evidence is needed for a verified stock;
unclassified SEC instruments remain unverified, known non-stocks are excluded.
This conservative source set may produce low verified coverage: do not relabel
funds, receipts, preferreds, units or warrants by company name to improve it.
Report listings and distinct issuers separately. Coverage JSON includes unique
verified-issuer sector / LEI / HQ counts divided by the SEC denominator, alongside
listing-level field completeness. Launch proposal requires >=80% verified issuer
coverage, >=70% sector completeness among verified listings and no unresolved
identifier conflicts. The full denominator can contain non-stock filers; its
scope is deliberately not silently reduced to inflate the launch percentage.

UK: qualified XLON statements from Wikidata, linked to GLEIF by exact LEI.
No licensed official LSE denominator exists. Report verified counts and field
counts, **without a UK percentage or a full-coverage claim**; status at most
partial. Companies House is UK-only and optional: the runner must find both the
official OGL v3 link and dataset-specific Free Company Data Product licence
wording. A generic OGL footer is insufficient. Otherwise report the gap and
continue with Wikidata/GLEIF only. Join by explicit P2622 company number, never
name; registered address is never treated as HQ. Download no authenticated API.

## Run and review (no publication)

After review/merge by the owner, GitHub backend repository → Actions →
**US UK Markets registry (artifact only)** → Run workflow. Choose the reviewed
ref and `max_download_mb=6144` (256–8192 MiB allowed). Only `workflow_dispatch`
exists, `permissions: contents: read`, no secrets, schedule or deploy step.
No workflow was dispatched as part of implementation. A new workflow normally
needs to be on the default branch to appear in GitHub's dispatch UI.

The runner performs ingest → normalisation → typed reconciliation → validation
→ immutable `versions/<UTC>-<hash>/`. It restores/saves the last two validated
versions via the dedicated cache; a failed run never saves a replacement cache
or activates a cloud pointer. Cache eviction is possible; keep the downloaded
last-good artifact rather than treating Actions cache as permanent storage.
Raw downloads are isolated under `.local/markets-pilot/raw/`; the review artifact
contains their URL/hash/size/time manifest, not multi-GB raw ZIPs. Validated
output, coverage and failure reports are uploaded with 14-day retention. No
incomplete denominator or truncated Wikidata page set is accepted as complete.
Robots denial, redirects, rate limits, schema drift or budget exhaustion fail
closed. SEC bulk access may require a provider-accepted contact-bearing UA in a
later review; this runner uses the existing `InvestediaRobot/1.0` and does not
bypass a rejection. Official GLEIF full XML URLs are discovered from its manifest;
changed/ambiguous manifests require review, never guessed URLs.

Offline replay (clearly synthetic, publication prohibited):

```sh
python -m tools.markets_pilot.run --input tests/fixtures/markets-pilot/input.json --workspace /tmp/markets-pilot-check
python -m unittest discover -s tests -p 'test_markets_pilot.py'
node --test workers/live/test/markets.test.mjs
```

Inspect `build-result.json`, `coverage.json`, `manifest.json` (hashes, sizes,
source manifest, per-type counts), `records.json`, `fx-relationships.json` and
company/country shards. Financials use the latest actual 10-K accession only:
Revenues, NetIncomeLoss, Assets, Liabilities; annual flow duration 330–400 days,
same currency, same year-end and flow start. Preserve filing date, period,
accession and original SEC filing URL. Missing/ambiguous values are null with
reasons. No TTM or quarter/annual mixing. Older submission archive files are not
queried individually; absent annual filings remain explicitly missing.

## FX

ECB 90-day XML, currency units per EUR, rebased to USD. Pearson correlation of
simple daily returns, latest 30 return intervals, >=25 exactly aligned intervals,
abs(r)>=0.70. Exclude entire EUR, DKK, BGN, CZK and HKD currency series plus
currencies whose abs correlation with EUR (USD base) or USD (EUR base) is >=0.95.
This is a conservative tracker screen, not proof of a legal peg. Publish the
exclusion reasons and unfiltered EUR-base sensitivity, including shared-base
bias warning. USD itself has constant USD-base returns, so it cannot have a
meaningful USD-base correlation edge. Never invent one. No ownership share or
capital-flow inference from correlations or GLEIF parent links.

## Read-only API and manual publication boundary

Code/tests only; `MARKETS_API_ENABLED="false"`. No bucket/binding was provisioned.
Four GET routes: `/v1/markets/country/{US|GB}`, `/search`, `/company/{I:id}` and
`/connections/{US|GB}`. Default verified-only search; `verified=false` includes
unverified/conflicted rows with their labels. `hidden_unverified` uses the same
filters. Known non-stocks and delisted records stay out. Page default1, limit20,
search max100; company relationship and connection limits max50. Pin `version`
for pagination; changes return409. Filter postings and 16 row shards bound
subrequests; no whole-registry scan. Company details include all its listings.
Five-minute cache, ETag, stale-on-error bounded to24h; previous snapshot fallback
only within24h of activation. Freshness metadata keeps listing snapshot, WDI
periods, SEC filing dates, ECB as-of and calendar horizon separate. Calendars
in the existing snapshot end 2026-12-12 and must be refreshed separately before
claiming holiday-aware sessions beyond that date.

Future owner-operated publication requires a private R2 bucket exposed to the
Worker as `MARKETS_BUCKET`, existing `PRICES` or separate `MARKETS_KV` namespace,
and a separately approved deployment/flag change. Do not grant public bucket
access. Artifacts are read at `markets/<version>/...`; only the small
`markets:current` pointer is in KV. No per-company KV writes. The API never writes.

The publisher below is **plan-only by default**. It checks hashes, safe paths,
version and non-fixture eligibility. It needs no credentials to produce a plan:

```sh
python -m tools.markets_pilot.publish PATH_TO_VERSION --bucket OWNER_BUCKET --namespace OWNER_32_HEX_KV_ID
```

Only after separate owner approval: authenticate Wrangler securely outside git,
export the current KV `markets:current` JSON to a private local file (omit only
for the first publication), then use the same command with
`--previous-pointer PRIVATE_POINTER.json --execute --confirm MARKETS-PUBLISH`.
R2 uploads are immutable version keys; upload manifest last; activate one KV
pointer only after every upload succeeds. Failed uploads leave the pointer
unchanged. Keep prior version for rollback; do not delete it during activation.
No manual publish, deploy, KV/R2 write or API enablement was performed here.

## Attribution, budget and sizing

Frontend must display: **Wikidata (CC0)**; **GLEIF (CC0)**; **SEC EDGAR**;
**World Bank (CC BY 4.0)**; **ECB**. Also credit Companies House (OGL v3.0) if used,
with its retained official licence URL. WDI credit should expand to World Bank,
World Development Indicators; ECB to Source: European Central Bank, reference
rates, not executable prices. Retain existing calendar Apache licence/notices.
HQ coordinates are explicit Wikidata headquarters observations only, with no
exchange/capital or registered-office fallback.

Planning estimate, **not measured**: 20–45 Linux Actions minutes/build, hard
45-minute timeout; one run <=2.25% of2,000 minutes, two <=4.5%. Zero Gemini calls,
zero new paid services, zero secret inputs. SEC and GLEIF bulk products may use
several GB; default6GiB raw cap can fail and must not be raised beyond8GiB without
review. Streaming/selected ZIP members avoid retaining full companyfacts in RAM.
No guarantee full upstream products fit the runner, budget or timeout.

For 10,000 listings, assume2KB/listing plus10KB/issuer of company facts and
provenance, duplicated typed records/search shards: estimate100–300MB/version,
200–600MB for two retained R2 versions, plus raw downloads only on the runner.
Actual `manifest.stored_bytes` is authoritative, not that example. KV holds one
~200-byte active pointer (+ optional previous pointer), no company rows.
R2 object count roughly issuer_count +16 row shards +filter_count +10 metadata
objects; explicit publication uses that many R2 writes and **one KV activation**.
API requests typically need pointer+manifest+filter lists+1–16 row shards; edge
cache reduces object reads. Review actual account usage/free allowances before
any owner-approved publication; no resource was enabled or bill incurred here.

## Verification before branch push

201 Python tests pass (4 pre-existing skips); 64 Worker tests pass (all52 existing
plus12 pilot cases); Maven verify passes13 Java tests. The26 new Python cases
cover identity/stock visibility, SEC periods, immutable versions and publication
failure; Worker cases cover all routes, pagination, cache/fallback and flag-off
404 before storage reads. No new failures. Existing track-backfill tests emit
unclosed-file ResourceWarnings; they still pass and were not edited. Offline
fixture replay validated successfully and remains publication-ineligible.
