# Live Globe connections — draft delivery fix

Not investment advice. Branch `codex/connections-live`; no merge, deployment,
live upload, Actions dispatch or financial job was performed during development.

The robot already generates evidence-based lines using
`tools/globe-news/connections.py`. The pipeline now sends articles first and then
that generator's snapshot using `tools/push-connections-to-worker.py`. Both must
acknowledge success; any upload failure exits nonzero and remains visible in the
existing workflows. No schedules, Gemini calls, frontend commits or Pages builds
are added. Existing workflow secrets stay unchanged:

- `WORKER_URL`: existing public Worker base URL (normally `https://api.investedia.com`).
- `NEWS_INGEST_TOKEN`: existing GitHub secret, matching Worker secret `INGEST_TOKEN`.
- `GEMINI_API_KEY`: existing generation secret; connections generation remains deterministic.

No secret value is printed or stored in source. Redirects carrying credentials
are refused. `--check` is read-only and never contacts the Worker:

```
python tools/push-connections-to-worker.py --check
```

## Worker storage and read API

Authenticated `POST /v1/ingest/connections` validates the
`investedia.connections.v1` schema, bounded streamed JSON and every evidence row
before writing. It whitelists origin/destination/evidence fields, real source
publication times, known relationship types, confidence>=0.25 and distance>=100km.
It rejects sector-wide lines. Country labels are preserved exactly: existing
outputs contain both ISO codes and full country names; they are not guessed or
silently remapped. A missing direction becomes `unclear`, never an invented move.

KV key `connections` merges IDs and keeps publications within the last30 days,
relative to Worker time. Newer snapshots win corrections; late/stale uploads can
add missing IDs but cannot replace newer evidence or advance the timestamp.
Conflicting duplicate IDs in one upload are rejected. Invalid uploads and
capacity failures leave the existing snapshot unchanged. The small
`connections:meta` key supplies `connections_generated_at` in `/v1/news` metadata
and `/v1/status`; it is repaired on retry if an earlier metadata write failed.
KV is not a multi-key transaction: storage failure after the snapshot put can
leave newer valid lines with older metadata until a retry; no false upload
success is returned.

Limits:2MiB/request,10,000 retained connections and8MiB serialized retained
snapshot. Exceeding a limit fails visibly rather than silently evicting valid
30-day records or slicing the upload. Two KV writes per changed snapshot (blob
and metadata); identical replay does not rewrite either. These are safety bounds,
not a promise that maximum-size blobs fit the free plan's CPU allowance. Review
actual volume and Worker CPU/account usage before raising bounds. No service,
paid plan, R2 bucket or new credential is introduced.

`GET /v1/connections` serves the compatible raw snapshot shape with generation
metadata, not a second inferred graph. Missing/corrupt storage returns503, so the
frontend can fall back. Public reads do not write KV. Responses set
`Cache-Control: public, max-age=300` and
`Cloudflare-CDN-Cache-Control: public, max-age=300`. Successful ingestion deletes
connections/news/globe/status edge cache keys **at the ingest location**, just as
the current news ingest does. Cache API deletion is not a global purge; other
locations expire within300s under origin policy.

**Owner cache check:** Cloudflare → Rules → Cache Rules: ensure any rule matching
`api.investedia.com/v1/connections` respects origin cache headers or bypasses the
zone's4-hour override. An explicit Edge TTL override can supersede origin headers;
Codex cannot inspect or change that dashboard rule here. Do not treat these code
headers as proof the existing rule is corrected.

## Frontend and history boundary

The companion frontend branch reads the API first, validates/deduplicates IDs,
and uses static `connections.json` only on API/schema/timeout failure. A healthy
empty API response is respected. A newer in-memory API snapshot survives a
transient failure with an older/equal static fallback. Visible-page refresh is
bounded to once per5minutes; freshness text updates each minute in Layers.

24H/48H use the API snapshot;7D/30D also merge the existing connection-history
files, with live IDs preferred. Drawing still requires the matching real article
and applies the existing topic/region/time window. Retaining30 days of connections
does not itself deliver missing historical article files. This change does not
rebuild archives or fabricate articles to make unmatched lines appear. The optional
client-side impact inference fallback is not enabled; normal mode uses evidence
snapshots and fails closed if both sources fail.

## Review / owner release sequence

1. Claude reviews the backend and frontend draft PRs.
2. Only after owner approval: backend merge triggers the existing Worker redeploy.
3. Confirm the existing scheduled news run acknowledges both article and connections
   ingestion. No manual ingestion was run for this task.
4. Review `GET /v1/connections`, `/v1/news` metadata and `/v1/status`; confirm origin
   cache policy and actual generated timestamp. Check the dashboard cache rule above.
5. Owner approves the frontend release; inspect24H/48H lines and7D/30D history.

## Offline verification

206 Python tests pass (4 pre-existing skips),76 Worker tests pass, including9 new
connection cases: auth, validation, field whitelist, duplicates,30-day pruning,
capacity retention, cache purge/GET and status freshness. Five new Python cases
cover publication order, acknowledged upload, URL/body safeguards and visible
pipeline failure. Java verify is also checked before branch push.

Frontend review screenshots replay the unchanged real saved generator snapshot
from8Nov2026 and disclose that time; they simulate an API-delivered robot output,
not a live ingestion. Drawable event counts:24H47;48H118;7D278;30D380, identical
onPC1440/phone390 in both themes. Existing saved event-day gaps produce expected
404s in long windows; their exact dates are in the frontend checks.json. They are
pre-existing archive gaps, not replaced with invented events.

Final Java verification: all13 tests pass. The contract test found the newly
added metadata key missing in Java, so the read-only NewsService/MarketService
now return null for unknown live freshness. The assertion was preserved.
