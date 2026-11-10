# Regional article and connection recovery

Not investment advice.

Branch: `codex/regional-backfill`. Manual Actions workflow only; no schedule,
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
```

Or, once the workflow is available on main:

```sh
gh workflow run regional-backfill.yml --ref main \
  -f days=7 -f confirm=BACKFILL -F dry_run=true -F connections_only=false
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

- Existing `REGION_FEEDS`, `NEWS_FEEDS` and official `FEEDS` are reused and URLs
  deduplicated. This includes the `OFFICIAL_RE` regional sources now used hourly.
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

## Budget: 7 and 30 days

| Per run | 7-day request | 30-day request |
|---|---:|---:|
| New article ceiling | 150 | 150 |
| Existing correction ceiling | 150 | 150 |
| Actual Gemini generateContent attempts, including retries | at most 8 | at most 8 |
| Model-list requests | at most 1 | at most 1 |
| Input prompt ceiling per attempt | 65,536 UTF-8 bytes | 65,536 UTF-8 bytes |
| Maximum output tokens per attempt | 8,192 | 8,192 |
| Actions job ceiling | 25 minutes | 25 minutes |

A full 150-candidate generation uses up to six nominal 25-candidate calls; the
remaining two calls can analyse up to 80 existing articles if there are no
retries. Connections-only needs up to four successful 40-record calls for 150
records, with retries sharing the same eight-request budget. Relevance, feed
retention, existing deduplication and per-source balancing usually reduce work;
no hosted runtime was measured in this sandbox. The budget cannot be exceeded
by model retries, a 30-day lookback or a larger feed. The total per-run ceiling is 512 KiB of submitted prompt text and 65,536
requested output tokens across eight attempts. The API's actual usage
metadata is accumulated by model; failed requests without usage are explicitly counted.

Dry-run **also uses Gemini** on GitHub. A dry run plus confirmation has at most
16 generation attempts and a combined 50-minute Actions ceiling, roughly 2.5%
of a 2,000-minute monthly allowance. The service is the existing Gemini project:
no new paid provider/key is introduced. Dollar cost depends on that project's
model/plan and remaining free quota; no zero-dollar guarantee is made. Use the
reported tokens with the model's current price if billing applies. Local offline
tests consumed **zero provider/Gemini calls**. No workflow has been dispatched.

RSS commonly retains only 10–50 items or a few days. A 30-day input does not
create missing history or enable archive scraping. Dates not present in permitted
feeds stay missing and are reported. The workflow is a bounded recovery, not a
claim that worldwide 7/30-day coverage is complete.

## Offline verification

163 Python tests passed (4 pre-existing skips); all 45 existing Worker tests and
7 new regional-history tests passed (52 total); Java `verify` passed 13 tests.
The recovery-specific tests cover saved original dates/links, source preservation,
no page/photo fetching, inventory/robots skips, state and Worker deduplication,
48-hour routing, <=80-record batches, fixed budgets including legacy retries,
secret-output rejection, immutable cached/article/event fields, events/threads
artifacts, safe dry runs, unchanged schedules, capacity and idempotent repairs.
These checks do not prove live provider availability or deployed Worker support.
