# Proposed pipeline and sizing — no production implementation

Not investment advice.

Manual source audit → licence decision/version → bulk acquisition → typed
normalisation → identifier/class/freshness/duplicate/conflict validation →
reviewed versioned registry → cached read-only Worker endpoints. This phase ends
at audit artifacts. Nothing deploys, builds a registry or enables a schedule.

Use immutable source snapshots/hashes and a licence registry. Each normalised
assertion keeps source IDs and retrieval/update dates. Quarantine collisions;
invalid/stale/licence-unclear records cannot silently become verified. Launch
only a stock universe whose source denominator and classification are compatible.
Use complete bulk/delta files when offered; per-issuer calls are bounded schema
probes, not the proposed production ingestion strategy. Record manifest versions,
publication dates, schema/XSD, checksums and resumable checkpoints.

Store future full source/normalised snapshots and country/company search shards
in private R2, with only a small active-version manifest in KV. Do NOT create one
KV write per company on the free plan: that would exceed ordinary daily write
allowances and compete with existing prices/news. A Worker reads only relevant
versioned shards; edge-cache responses and paginate on the server. No full
registry is shipped to the browser. Build filter postings/sorted pages offline;
never scan a global registry for each Worker request.

Sizing **assumptions, not measured coverage or a quota guarantee**:

| Example inventory | Estimated uncompressed size |
|---|---:|
| 200,000 listing assertions × 800 bytes | 160 MB |
| 100,000 issuer/entity summaries × 1,200 bytes | 120 MB |
| Provenance/index/relationship overhead, comparable order | 100–300 MB |
| Three retained versions, excluding raw SEC/GLEIF bulk files | roughly 1.1–1.7 GB |
| KV manifest/pointer and a few small hot metadata keys | under 1 MB target |
| One country search response, 20 × ~650-byte rows + envelope | about 15 KB |
| One bounded company response, listings + annual facts | target 10–40 KB; paginate relationships |

These figures do not include potentially multi-gigabyte SEC archives. Do not
cache/parse an entire SEC ZIP or entire registry inside the Worker. Retention,
sharding, actual free allowances and existing account consumption must be
measured before choosing KV/R2 or enabling any refresh. No resource/account or
billing setting is changed here.

Manual `markets-audit.yml`: no secrets, `contents: read`, no schedule, concurrency
limit, 20-minute timeout. Maximum 20 Actions minutes per audit (two audits ≤40,
2% of a 2,000-minute monthly allowance). Expected duration is unknown until the
runner executes; local offline tests are not a network-runtime measurement.
No Gemini calls. A future production full-bulk build could take tens of minutes
or hours and needs a measured pilot; no “fits free” promise is justified yet.

Runner outputs are review artifacts only. It stores statuses, hashes, schemas
and audit-derived metrics, not a production registry or full unlicensed source
copies. HTTP failure, robots denial, redirect, 429/Retry-After and download-size
limits are recorded as missing evidence, never bypassed. The package's already
retained Apache licence/notices are the only locally checked reuse evidence;
current remote primary terms await the runner and review.
