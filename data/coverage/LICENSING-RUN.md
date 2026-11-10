# Primary source licensing evidence

`source-licensing.yml` is manual, read-only and has no new secrets, schedules,
models, publication, ingestion, financial job, deploy or repository write. It uses
the runner's ephemeral read-only GitHub token only to restore the latest successful
coverage inventory artifact. Missing inventory stops before provider requests.
The existing robots remain unchanged; no new feed is enabled.

The collector enumerates95 currently configured regional/official feed URLs plus
FRED-series and ECB-policy-rate notices (97 audit rows). It honours disabled,
unavailable and robots-disallowed inventory entries. It checks robots for the
source/notice path, defers explicit crawl delays/rate policies for manual spaced
review, never reads RSS/article pages, follows no redirects, and considers at most
two same-host legal/copyright/licensing links found on each provider's home page.
An explicit cross-host ECB legal notice gets a separate robots check. Source URLs
must use public HTTPS; no credentials or nonstandard ports. Requests use
InvestediaRobot/1.0, 1MB/response,15s timeout, host cache/one-second minimum spacing,
and a12-minute collection budget inside a15-minute job. Raw primary notices and
hashes are separate from the review manifest. Known private credential values in
responses/reports are rejected without printing them.

A phrase such as “non-commercial” or “all rights reserved” is a **review signal**,
not an automatic finding that short attributed article summaries are forbidden.
HTTP200, an RSS link, or a generic Creative Commons sentence cannot grant rights
for every embedded work. The report's commercial-use field stays null until a
person reviews the exact dataset/notice scope. It never authorizes a source.
No source terms were fetched in this sandbox: direct source access is blocked.

## Owner/Claude action after reviewing and merging

Run Actions → Source licensing evidence (manual review only), no inputs. Download
`source-licensing-<run id>`; inspect report.json and the raw-index/hash-linked notices.
Record, per feed, the exact primary URL, fetched/review date, headline + short
summary + source-link commercial display scope, attribution/length/API limits,
third-party exceptions and a clear allowed/conditional/forbidden decision in
SOURCE-LICENSING-AUDIT.md. Flag forbidden uses before any source is newly enabled.
If a legal notice is behind a redirect, different hostname, crawl policy, PDF or
JS-only page, finish that source manually rather than treating it as cleared.

For rates, review DGS2/DGS10/DFEDTARL/DFEDTARU source-specific FRED rights and the
ECB FM.B.U2.EUR.4F.KR.DFR.LEV notice. The existing FRED_API_KEY is not a blanket
redistribution licence. These are source references only: this collector does not
fetch yield/rate observations, implement a price pipeline or publish rates.
Actual rate delivery remains blocked on current source evidence and review.

Offline enumeration: `python tools/coverage/source_licensing.py` (zero requests).
With an approved inventory on a network-enabled runner:
`python tools/coverage/source_licensing.py --fetch --inventory data/coverage/feed-inventory.json`.
Expected cost: zero Gemini calls and new secrets, no daily Actions minutes;
manual job hard maximum15 Linux Actions minutes. No workflow was dispatched here.
