# One-off outage recovery — staging only

This branch does not deploy, enable schedules, run Gemini, or ingest live data.
The broad P3 history/backfill and financial jobs remain blocked. The existing
hourly workflow is unchanged. No frontend commits/builds occur per news update.

## Boundary evidence (UTC)

The requested **bounded search window** is `[2026-11-08T16:00:00Z,
2026-11-09T21:30:00Z)`. It is not yet a verified continuous outage:

- Recovered old-repo commit `d46cc360f27caa2b2a6ee23f5ce32238b7f11ad3`
  was committed at November 8 16:16:34. Its `news-live.json` has `updated_at`
  **16:12:24**, with newest original publication **16:00:00**.
- The recovered `archive/main` also has a later live feed at commit
  `09e95de751321df2d40186d9e4e62ab6ec676920`, committed November 9
  **17:58:10**, generated **17:55:24**, newest publication **17:52:00**.
  Thus the recovered robot was producing records within the proposed gap.
  Whether those updates reached the public site is unverified.
- The recovered old `news-archive.json` still reports November 8 **16:12:24**.
  Its 1,500 records, the later 360-record live feed, and the November 8 live
  feed were reduced to 4,610 ID/URL/headline dedupe keys in
  `data/news-gap-archive-index.json`. These are not uploadable articles.
- The read-only workers.dev `/v1/news` check reports generation/fetched time
  November 9 **22:57:37**, 40 articles, original publication range November 7
  **20:40:51** through November 9 **22:49:00**. This current meta does **not**
  prove the first successful run at 21:21. The owner must verify that run's
  Actions log/artifact before confirming the end boundary.
- `https://api.investedia.com/v1/news` is blocked by this environment's current
  allowlist. Fetching the now-private old repository also fails; no old remote
  workflow was run. Evidence above uses the already recovered Git objects.

## Implementation and safety

`tools/news-gap-backfill.py` reuses the priority producer's literal source
configuration, `news_core.py` URL canonicalisation/relevance rules, and the
existing redirect-refusing, authenticated `push-news-to-worker.py` transport.
`tools/news_gap_history.py` ports **only** read-only P3 geography guards from
`tools/backfill_history.py` on recovered `codex/p3-news-backfill`
(`9904e9770`). It never runs that broad archive writer. It rejects an origin
unless exactly one country is named in the article body (excluding site header,
footer and navigation); publisher geography is never used as origin evidence.

Only original RSS pubDate/DC date or Atom published timestamps are accepted;
Atom updated, retrieval time and GDELT seendate are never substituted. No
clamping/redating. Article URLs must return 200 without redirects, belong to
the corresponding source's approved hosts, and provide article/main text.
The original headline, source link and publication time are retained. No
article body, generated summary, investment call, forecast or price is stored.
`backfilled`, `backfilled_at`, and `backfill_provenance` are additive metadata.
The frontend's existing news-source merge retains article fields, so these
flags remain available for a later visible late-added label.

Source requests are paced at six seconds per host; at most 80 new candidates
are inspected per stage. A limit or unavailable source is visible in the report;
any unavailable feed makes the scan incomplete and exits nonzero. There is no
claim of complete historical coverage from today's limited RSS retention.

Every accepted article requires human relevance/country judgments in the
hash-bound review. The gate is at least 90% relevant and 95% correct country
across **all** staged articles; even after that gate, known bad individual
records are excluded from upload. Empty batches fail review. Gemini calls and
provider cost: **0**. No Gemini key is passed to this workflow.

The Worker patch is necessary: the current endpoint would replace/cap the feed
at 40. The proposed `gap-history-v1` mode writes a separate `news-gap-history`
KV key (maximum 240 articles, never silently truncated) and merges it into API
reads. It never rewrites current news or its freshness clock. Ordinary hourly
writes retain the separate historical records. Server-side ID/URL/headline
checks make retries idempotent. The runner refuses legacy Workers without
`GET /v1/ingest/news/capabilities` returning `history_ingest_version=1`; it will not accidentally send a historical
batch to the replacement endpoint. **A separately owner-approved deployment
is required before confirmation can work. This task performs no deployment.**

## Actual one-hour staging attempt

Command executed (no ingestion secret used):

```sh
python tools/news-gap-backfill.py \
  --start 2026-11-08T16:00:00Z --end 2026-11-08T17:00:00Z \
  --worker https://investedia-live.adonaykabeya10.workers.dev \
  --archive assets/globe/news-archive.json \
  --archive data/news-gap-archive-index.json \
  --output .local/news-gap/one-hour
```

| Measure | Result |
|---|---:|
| Feed candidates available for this hour | 0 |
| Accepted | 0 |
| Duplicates encountered | 0 |
| Article rejections | 0 (no source items could be fetched) |
| Feed requests unavailable | 7 of 7 |
| Gemini calls | 0 |
| Worker writes | 0 |

The scan exits nonzero as incomplete, saving `staged.json` and
`review-template.json`. **Five accepted article examples cannot be supplied**
from an inaccessible source population; no placeholders were invented.
No measured relevance/country percentage is claimed. Source-access failures
are separate from unit/Worker tests, which pass.

Attempted feeds: ECB press releases; Federal Reserve all releases, speeches,
and monetary releases; BBC Business; Guardian Business; MarketWatch top articles.
Exact feed URLs/statuses are in the staged report. Before retrying locally,
allow `api.investedia.com`, `www.ecb.europa.eu`, `www.federalreserve.gov`,
`feeds.bbci.co.uk`, `www.bbc.co.uk`, `www.bbc.com`, `www.theguardian.com`,
`feeds.content.dowjones.io`, and `www.marketwatch.com`. Keep existing domains.
The ingest secret is currently scoped only to workers.dev; using the API custom
hostname locally also requires that hostname in its secret destination scope.
Do not paste keys in chat, change their values or rotate them for this task.

## Operator steps after review

Claude opens a draft PR from `codex/news-gap-backfill`. The dispatch-only
workflow must become available on the default branch through a separately
approved merge; this branch does not merge itself. No schedule is added.

1. In backend Actions, choose **One-off news gap recovery**. Start with
   `start=2026-11-08T16:00:00Z`, `end=2026-11-08T17:00:00Z`, `confirm=false`.
   Reuse existing GitHub secret `WORKER_URL=https://api.investedia.com`.
   Stage first, then inspect coverage before widening within the fixed window.
2. Download `news-gap-stage`. Check original source times/URLs, review every
   staged record, and fill `review-template.json`: named reviewer, each boolean
   judgment, `boundaries_verified=true` and a concrete `boundary_evidence`
   reference to the archived feed and successful Actions log. Preserve the
   artifact hash. Do not regenerate staged articles during confirmation.
3. After the owner approves the actual report and the separate Worker capability
   is deployed, run the **same workflow** with `confirm=true`,
   `staging_run_id=<the successful staging run ID>`, and
   `review_json=<the completed review-template.json contents>`.
   The confirmation downloads that exact artifact, validates its hash/review,
   rereads current Worker news for duplicates, then ingests history only.
   Existing GitHub `NEWS_INGEST_TOKEN` must match Worker `INGEST_TOKEN`.
   No other secrets are required. The review is data, never shell code.
4. Check the API for retained original publication times and provenance flags.
   Verify the main feed's generation timestamp was not advanced by the backfill.

Both staging and confirmation share the hourly producer's concurrency group,
cap the job at ten minutes, and visibly fail on errors. Inputs never change the
hourly schedule. Artifacts are retained for 14 days. Source availability and
complete boundary verification remain blockers; no full-window scan or live
confirmation was performed.
