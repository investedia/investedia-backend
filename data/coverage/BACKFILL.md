# Regional article and connection recovery

Not investment advice.

Branch: `codex/regional-backfill-fix` (continuation of regional recovery). Manual Actions workflow only; no schedule,
deploy, frontend commit, backfill execution or live ingestion is performed by
this branch. The priority and broad schedules stay unchanged. All provider/model
execution is on GitHub's runners; tests here use saved fixtures only.

## Before running

1. Claude opens the draft PR. The owner reviews/merges separately.
2. A **separately approved Worker deployment is required for regional history**.
   The old `gap-history-v1` only accepts November 8–9 and ignores repeated IDs;
   using it unchanged would lose older records/connection corrections. This
   branch adds the authenticated `purpose=regional-backfill` option to that
   same mode/KV key, bounded to the previous 30 days. The old outage whitelist
   stays unchanged. A run-start window must be no longer than 30 days and no more
   than 30 minutes old at ingestion, allowing the bounded model job to finish.
   It keeps the 80-record/request, 400,000-character payload
   and 240-history-record limits; no eviction, capacity increase or financial
   job is introduced. Capabilities expose the supported versions and capacity.
3. Run **Coverage fetch (review only)** first, inspect its feed inventory, and
   retain the successful `coverage-review` artifact. The backfill uses the
   checked-in `data/coverage/feed-inventory.json` if present; otherwise it
   downloads the latest successful coverage-fetch artifact using the built-in
   read-only GitHub Actions token. It never treats a missing inventory as proof
   that all feeds are allowed. Expired/missing inventory fails visibly.
4. Keep these existing GitHub secrets: `GEMINI_API_KEY`, `WORKER_URL`, and
   `NEWS_INGEST_TOKEN` (must match Worker `INGEST_TOKEN`). No new secrets,
   repository variables or paid services are needed. Never paste values into
   workflow inputs, reports, source files or chat.

## Dry run first

In backend Actions choose **Regional article backfill (manual)**:

```text
days: 7
confirm: BACKFILL
dry_run: true
connections_only: false
gemini_model: ""  # reads the last successful live/hourly status model
gemini_calls: 20
batch_size: 25
```

Or, once the workflow is available on main:

```sh
gh workflow run regional-backfill.yml --ref main \
  -f days=7 -f confirm=BACKFILL -F dry_run=true -F connections_only=false \
  -f gemini_calls=20 -f batch_size=25
```

Download `regional-backfill-review`. Inspect `report.json`, `new-articles.json`,
`connection-repairs.json`, `connections.json`, proposed event day files and
`threads.json`. The report includes original oldest/newest retained dates per
feed, inventory skips, source failures, candidate/duplicate/cap deferrals,
counts by feed/region/country/day, samples with original links, connection
percentages by region, checked records still without links and reasons,
Gemini requests/token usage and elapsed time. Counts from a dry run describe
**proposed** changes, not live coverage. An oldest retained item before the
start does not prove that the feed contains every intervening article.

After reviewing the dry run, the owner can run the same inputs with:

```text
dry_run: false
```

This refetches/reanalyses within the same budgets; it does **not** replay a
hash-locked artifact. Review its resulting report too. `generated_at` for normal
ingest is the current Worker's `meta.fetched_at`: an old article never makes
the feed's update clock newer. Each acknowledged batch updates the backend
cached event archive immediately; a later failure is reported and acknowledged
state survives. Retry uses source IDs/URLs and saved analysis markers.

To repair existing missing/empty impacts without fetching feeds or generating
new articles:

```text
days: 7
confirm: BACKFILL
dry_run: true
connections_only: true
```

Review, then repeat with `dry_run=false`. This mode does not require a feed
inventory artifact. It checks the live Worker response (which includes history),
the live/48h/archive snapshots and the retained history sidecar. It only copies
`impacts`/`ripples`/`sectors` back to existing records; headline, summary, id,
original date, source and location remain unchanged. Valid empty analyses are
recorded separately to avoid paying repeatedly for the same unsuccessful case.

## Source and evidence rules

- Existing `REGION_FEEDS` and official `FEEDS` are reused and URLs
  deduplicated, with regional sources first. Non-official global/US publisher feeds
  already handled hourly are excluded from this recovery. This includes the `OFFICIAL_RE` regional sources now used hourly.
  No invented feed, GDELT date, article-page scrape or unofficial archive crawl.
- Inventory entries marked unavailable/disallowed/disabled are skipped. Remaining
  feeds are checked against robots.txt; disallowed, inaccessible, HTML/redirect
  robot responses are skipped. A 404 robots file follows normal no-file rules.
  Crawl delay/request rate are respected; excessive waits are explicitly deferred.
- Only RSS pubDate/DC date or Atom **published** is an original timestamp. Missing,
  timezone-less, invalid or future timestamps are rejected. Atom updated,
  retrieval time and a clamped "now" are never substitutes.
- Existing `pick_stories` generates summaries and validates locations. Its new
  opt-in source-preserving/feed-only options retain exactly one original feed
  item per article, with the original headline, link and publication instant.
  These options do not change the normal robots' behaviour. Source/region tags
  remain balancing hints, never event-location evidence.
- Existing `backfill_impacts` handles both absent and empty impacts in recovery
  mode. The evidence-only resolver is ported from `codex/news-connections`
  (`97e6d18`); the same `tools/globe-news/connections.py` rules calculate lines.
  An impact needs a named asset in the supplied reporting and a real finite
  positive saved price. Generated summaries cannot manufacture naming evidence
  for a new feed item. No generic country/bank/oil-major links are inferred.
- Broad sector-only links remain rejected by the existing engine; there is no
  separate invented ripple/sector schema. Same-place assets can remain event
  dots without a drawn line. Rejections distinguish unsupported naming, missing
  prices, unresolved/broad assets and existing drawing rules. Retrospective
  impacts are always non-scorable; frozen V5 / Track Record are untouched.

## Routing, persistence and capacity

Articles at least as recent as the current-clock 48-hour boundary use normal
ingest; older articles use `gap-history-v1` / `news-gap-history`. Requests contain
at most 80 records and are split further below 350 KB, including protected
originals for archived connection corrections. Server-side regional corrections
reject changes outside the connection fields. Local archive-only originals can
be restored with their protected original record and new impacts; they consume
history slots like any other addition. Idempotent retries do not duplicate them.

History is still limited to **240 total records**, shared with existing outage
imports. The artifact reports available slots and every deferred ID. A confirmed
run can ingest the accepted subset but never evicts or truncates stored history;
its report explicitly labels partial capacity. Empty/newer rolling records do
not substitute for older history. Unknown capability/capacity blocks historical
writes until the Worker is updated. No background deploy is triggered here.

All three workflows use `news-production`, with identical expanded cache paths
and the `priority-news-state-` prefix. A legacy five-file restore protects the
existing state when the expanded cache's path-version fingerprint first changes.
Dry runs restore without saving. Confirmed runs retain acknowledged history,
events, threads and analysis markers; normal robots preserve that shared state.
The normal rolling/48h cache representations only receive connection-field
patches; dates/headlines and feed update timestamps are not re-written.

**Frontend delivery limit:** current Globe country-history and Story-thread
readers still fetch static Pages `events/YYYY-MM-DD.json` / `threads.json`.
This workflow updates and preserves the **backend** events archive and provides
it as an artifact, while article history/impacts are delivered through the
Worker API. Updating the cache alone does not publish those static archive files.
A separate Worker archive API/frontend reader bridge is needed for those static
views to consume the new archive without per-run Pages builds. No frontend
commits/builds or deployment are silently added by this workflow.

## Model, regional reserves, repairs and cost

The previous job's eight-call budget was consumed by failed model fallbacks,
then repair ran only if generation left a call. This made articles_checked zero.
Now repair runs first, scanning the live Worker response (including KV gap
history), local live/48h/archive and history sidecar over the last 30 days even
when fetching only 7 days of new feed items. Missing files and per-source counts
are explicit. At most150 existing articles are submitted for repair; protected
editorial fields stay unchanged. An unchanged prior no-link judgement is reported
separately and does not cause another paid analysis.

Model selection: exact `gemini_model` input, otherwise live `meta.model`, then
saved priority status, then the last successful saved robot model. No guessed model
names or generation probes. Missing model fails before any Gemini call. A pinned
model transport failure stops immediately after one request, not a list of fallbacks.
Model discovery is unused (zero); its safety wrapper permits at most one actual
list request. `selected_model`, `actual_model_used`, per-call candidate counts,
purpose, request/token usage and failures without usage are reported.

New candidates are taken round-robin across source hints af/latam/me/asia/oc/eu.
These are balancing hints only, never event location. Global official fallbacks
are last and limited to min(15, regional_selected/4); thin regional feeds do not
hand their reserve to global publishers. At most150 new candidates are selected.
`processed_by_region` / `deferred_by_region` describe source hints; `by_region`
describes validated event locations. Actual accepted geography can differ and is
never forced. Review the new report against the majority-regional acceptance goal.

| Limit | 7-day or 30-day run |
|---|---|
| New article candidates | 150 maximum |
| Existing repair submissions | 150 maximum, scanned over30 days |
| New candidates per call | input batch_size, default25, range1–40 |
| Generation/repair HTTP calls | input gemini_calls, default20, hard maximum40 |
| Model list calls | zero normally, hard maximum1 |
| Prompt bytes per call | 65,536 maximum |
| Requested output tokens per call | 8,192 maximum |
| Actions timeout | 25 minutes, model requests stop after24 minutes |

Nominal full work: six25-candidate generation calls plus four40-record repair
calls, **up to10 calls** before validation/caps reduce work. Default absolute
ceiling20 calls =1.25MiB submitted prompts /163,840 requested output tokens;
maximum override40 calls =2.5MiB /327,680 tokens. These are bounds, not measured
usage or a promise that all candidates will be selected. Actual usage is in the
artifact. A dry run plus confirmation doubles the selected call budget and has
an absolute50-minute Actions ceiling. No daily cost or schedule is added. Existing
Gemini plan/free quota determines billing; no new provider/key is needed.

RSS often retains only10–50 items or a few days. Thirty days does not reconstruct
missing feed history or authorize archive scraping. Local offline checks consumed
zero provider/Gemini calls. **Nothing has been dispatched or ingested by Codex.**
The task brief explicitly requires code/offline verification only; a new hosted
dry run remains an owner action after review/merge. The GitHub API also currently
returns Forbidden here. Do not claim the live regional-majority acceptance result.

## Offline verification

212 Python tests pass (4 pre-existing skips), including25 regional recovery tests;
all76 Worker tests pass; Java verify passes13 tests. Existing unclosed-file
ResourceWarnings remain in news_core/events/older tests; no new failures.
Coverage includes pinned-model failure, zero/one discovery, bounded inputs and
per-call context, regional reserves, normal-mode missing-impact repair, source/date
preservation, inventory/robots exclusions, dedupe,48h routing,80-record batches,
secret-output guards, immutable cached/article/event fields and idempotence.
No user interface changes; review artifacts replace UI screenshots for this task.
