# Proposed read-only Markets API contract — not implemented

Not investment advice. Direction C/right inspector with A tables. Stocks first;
ETF/bond filters are unavailable pending validation. No Worker code changes.

Common envelope:

```json
{"data":null,"meta":{"schema":"markets/v1","version":null,"updated_at":null,"stale":true,"source":[],"coverage_status":"not yet","reason":"audit_not_approved"}}
```

Every record has `verification_status`, source summaries and independent stale
state. Every assertion retains source/source_id/retrieved_at/validation_status.
Null data has a reason; zero is used only when actually measured. Use ISO dates,
ISO4217 currency codes, explicit period and units, and IANA zones. Response version
must be consistent across page/count results; no mixed registry snapshots.

| GET | Proposed response |
|---|---|
| `/v1/markets/country/{iso2}` | Country ID/name, exchanges[{mic,name,country,timezone,sessions,calendar_as_of}], currency, economy[{indicator,value,unit,period,source,as_of}], per-field coverage flags, updated_at. Unsupported territory mapping gives explicit unsupported/null, not a guessed country. |
| `/v1/markets/search?country=&sector=&type=stock&exchange=&currency=&verified=true&page=&limit=` | rows[{id,issuer_id,issuer_name,security_id,ticker,mic,sector,currency,isin,lei,verification_status,stale,source}], total, hidden_unverified, page, limit, next_page, version. Sector includes source taxonomy/version. |
| `/v1/markets/company/{id}` | legal_entity, issuer, all validated listings (MIC/ticker/currency/validity), sector, reported HQ (location kind/source/precision), reported parent relationships, SEC annual financials or null+reason. Cap initial relationship rows and provide pagination. |
| `/v1/markets/connections/{iso2}` | corporate[] and currency[] separate. Corporate: child/parent IDs, direct/ultimate relationship type, source/status/period; currency: ISO4217 pair, Pearson r, method, base, window, aligned observations, as_of, source. No ownership percentage or capital-flow implication. |

`verified=true` is the default. `hidden_unverified` counts unverified/conflicted
eligible stock rows under the SAME non-verification filters and snapshot; it is
not an unfiltered global number. With inclusion enabled, hidden_unverified is 0; a separate total_unverified preserves the toggle count. Explicit `verified=false` means include those
rows, still labelled; rejected rows never appear. `total` describes the returned
visibility scope, with `total_verified`/`total_including_unverified` available to
avoid ambiguity. Missing verification status is not silently verified.

Validation: ISO2/MIC/currency allowlists; type=stock only initially; page >=1;
limit default 20/max 100; stable `(issuer_name, listing_id)` order tied to version.
For deeper traversal prefer an opaque versioned cursor; reject stale page/cursor
versions with 409 rather than duplicate or skip results. Reject unknown filters,
malformed IDs and unsupported type with 400/422; do not silently broaden search.
No browser-side download of the whole registry. Use cached count/filter indexes.

Proposed errors:

```json
{"error":{"code":"coverage_not_available","message":"Verified listings are not available for this market.","reason":"licensed_source_missing","retryable":false},"meta":{"version":null,"stale":false}}
```

400 invalid_query; 404 unknown_entity; 409 version_changed; 422 type_not_available;
429 rate_limited with Retry-After; 503 no_valid_snapshot. Preserve the last good
response on upstream refresh failure, marked stale; never replace it with empty
success. Unsupported country is distinct from a measured empty listing set.

Proposed cache: immutable versioned internal shards; country/company/search/
connections API TTL 5 minutes with ETag and bounded stale-on-error up to 24 hours.
Publish source-specific freshness flags: daily listing snapshots, annual WDI,
filing-dated SEC facts and ECB publication-day rates are not interchangeable.
Target payloads: country 5–15 KB, search page20 ~15 KB, company10–40 KB, bounded
connections <10 KB. These are budgets to measure in a later pilot, not actual
benchmarks. Do not load a registry globally to compute counts on each request.
