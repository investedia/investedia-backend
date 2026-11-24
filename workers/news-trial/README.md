# Isolated priority-news trial

This is preparation only. It does not deploy, generate news during CI, change the live Worker, publish articles, send alerts, or disable GitHub jobs. Owner approval is required before creating resources, adding secrets, deploying, or enabling generation.

The older `workers/live/v1/news.js` prototype is not equivalent to the Python producer: its sources, IDs, retention, archive and connection handling differ. This container runs the current `update_globe_news.py` priority or broad tier and `tools/globe-news/connections.py` unchanged. The usual `tools/news-pipeline.py --run` wrapper is deliberately excluded because it also ingests into production.

## Isolation

- Separate Worker `investedia-news-trial`, Durable Object and private R2 bucket of the same name. No production routes, KV, Supabase, ingest token, alert credentials or publishing scripts.
- `TRIAL_ENABLED = "false"` and no cron triggers. Every public endpoint requires a separate `TRIAL_TOKEN` secret, including health/results. The HTTP API accepts no input files, URLs, environment or commands.
- Container Internet access is disabled. HTTPS interception permits GETs only to exact declared producer-source hosts, plus Gemini model listing/generation. Redirects are checked again; production destinations, bare IPs and other writes are denied. The real Gemini key stays in the Worker and is injected only into Gemini requests; the Python process gets a proxy placeholder.
- Docker copies an explicit list of source/reference files. Its matching ignore file excludes everything else, including `.git`, local configs and secrets. No GitHub/Cloudflare credentials enter the image. It runs as an unprivileged user.
- Each run creates disposable files, retains original article timestamps and IDs, and saves artifacts only under `trial/` in the new bucket. Failed generation does not advance trial state. No empty/no-source run counts as a successful comparison. The container stops in `finally` and has an inactivity limit.
- One manual run at a time, no automated retry and no automatic schedule. This limits the initial trial's API/container spend; Workers Paid does not make container use unlimited.

## Offline checks

From repository root:

```text
python workers/news-trial/runner.py --preflight
python -m unittest discover -s tests -p test_news_trial.py
node --test workers/news-trial/policy.test.mjs
docker build -f workers/news-trial/Dockerfile -t investedia-news-trial-check .
docker run --rm --network none --read-only investedia-news-trial-check python workers/news-trial/runner.py --preflight
```

The PR-only workflow builds locally on the GitHub runner, without credentials, registry push or deployment. Tests use real saved seed data; they do not generate financial news. The local Docker engine must be running for the last two commands.

## Operation after explicit deployment approval

Use Wrangler **4.136.0 or later** for the direct Durable Object Container API. Configuration follows [Cloudflare's API](https://developers.cloudflare.com/containers/api/durable-object-container/) and [configuration reference](https://developers.cloudflare.com/workers/wrangler/configuration/#durable_object-scheduling-policy).

Create only the separate private trial bucket and deploy only this configuration. Keep its preview/public R2 access off. Add `TRIAL_TOKEN` (new independent random token) and `GEMINI_API_KEY` through Cloudflare's secret store; never put values in files or chat. No production credential is needed. Keep generation disabled for the first health check.

The manual **Export isolated news trial seed** GitHub workflow restores the exact cache of the latest successful priority workflow run read-only (no broad prefix fallback to unrelated backfills), rejects missing or more-than-six-hour-old priority success, and packages a private `isolated-news-trial-seed` artifact retained for one day. Run it on `main` after a successful priority run. It does not call Gemini, save the cache, publish, or deploy. Download and inspect the artifact before uploading the seed to the isolated R2 bucket.

Prepare a fresh seed from the latest successful producer cache, not an old repository snapshot. Restore the cache into a disposable checkout without running the publisher, then execute:

```text
python workers/news-trial/runner.py --pack <temporary-seed-path>
```

This command only reads saved JSON and writes a local package. It excludes the historical article library (not needed by priority generation), includes event/seen/photo state, and enforces a 32 MiB compressed-transfer limit plus a 128 MiB expanded-data limit. Upload it privately as `trial/seed.json.gz` in the trial bucket after approval. Do not commit it. Reference data and registry are copied from the image's reviewed commit. The seed's dates are never rewritten to make it appear current.

Authenticated endpoints on the trial Worker's workers.dev address:

| Method | Path | Result |
|---|---|---|
| GET | `/health` | Trial enabled/disabled; confirms there is no schedule |
| POST | `/run` | One priority generation, only after explicitly enabling `TRIAL_ENABLED` and adding both secrets |
| POST | `/run?tier=broad` | One broad generation; shares the same locked trial state, never publishes |
| GET | `/result` | Last successful gzip-compressed JSON artifact: full trial files, connections and measured summary |

Send `Authorization: Bearer <trial token>` securely; do not place the token in the URL or terminal history. `/run` waits for the producer, so use a client with a sufficiently long timeout. A failed request is not automatically retried. `trial/state.json.gz` resumes the trial's own seen/archive state on later runs; production continues independently. To restart from a fresh seed, remove only the trial state object after reviewing/saving the old artifact.

## What remains to prove

Docker/runtime checks, HTTPS interception/certificate support and real-source redirect behavior must pass in the deployed isolated environment before any comparison is trusted. Source descriptions hosted outside the exact source allowlist are blocked; the producer retains its normal description fallback. Review failed-source diagnostics and extend only specific verified publisher hosts if needed. No Pixabay downloads are allowed; existing photo references are reused just as in the priority GitHub workflow. The container does not serve photo files or a website preview.

This is a manual first trial, not the completed 24-hour comparison or a replacement scheduler. Before a production switch, compare source failures, new article IDs/counts, countries/regions, archive/library, photo references, connections, errors and duration over representative runs. Show website previews when wiring any alternative feed. Only after a successful comparison and a separate owner approval may production ingestion or schedules change. This PR makes neither change.

The real producer state can exceed 32 MiB uncompressed. Seeds/results now use gzip without trimming articles, events or timestamps. The Worker stores opaque compressed bytes and parses only a small summary header; the container enforces both compressed and expanded size bounds. Legacy raw JSON seeds remain readable. The container uses the `basic` (1 GiB) instance to accommodate parsing the archive, and still stops after every run. This uses more resources than the old `lite` setting; actual trial cost and peak memory must be measured before scheduling. The trial still has no automatic schedule or production credentials.

Use Wrangler to enable/disable the trial, preserving the full Container/exports/image configuration:

```text
npx wrangler@4.136.0 deploy --config workers/news-trial/wrangler.toml --keep-vars --var TRIAL_ENABLED:true
npx wrangler@4.136.0 deploy --config workers/news-trial/wrangler.toml --keep-vars --var TRIAL_ENABLED:false
```

A generic settings-only API patch omits Container image metadata, and caused the first runtime startup failure. Always restore the disabled configuration after a manual test. Never copy these trial controls to the production Worker.

The first completed isolated priority run produced two new articles, retained 358 existing publication dates without duplicate IDs, saved 360 library entries and built 291 connections. It exposed 31 source failures versus two in its GitHub seed: the old proxy omitted the appended official-region feeds. The allowlist now includes all explicit producer feed hosts (including appended lists), with a regression check against the Python definitions; it permits GETs only. Legacy HTTP feed requests are intercepted and upgraded to HTTPS; arbitrary HTTP, nonstandard ports, production hosts and publisher writes remain blocked. Broad trials use the unchanged broad tier, including GDELT, and share the same Durable Object lock/state with priority. Failed runs report only a fixed stage and tier, never raw logs, URLs, keys or prompts. Coverage and broad-runtime parity still require real checks before any live switch.


## Isolated calendar adapter

`POST /run?job=calendar` and `GET /result?job=calendar` use only `trial/calendar/` storage and a separate `calendar-trial` Durable Object instance. Load a gzip seed with exactly `files.calendar-live.json` from a validated production calendar readback; never use invented observations or overwrite its event dates. The adapter runs the existing `update_calendar.py`, `calendar_official.py` and `calendar_fred.py` unchanged in disposable storage. It rejects runs with no fetched official events, swallowed event-generation failures or stale output, rather than counting retained old data as a successful refresh. No calendar ingest or schedule is added.

Unlicensed feeds remain off, matching the current GitHub configuration. `FRED_API_KEY` is optional for an initial official-schedule trial, but must be supplied as a Cloudflare Secret before claiming parity with any production FRED enrichment. The real key remains in the Worker: only the two fixed read-only FRED endpoints receive it, and FRED redirects are rejected. The container sees a placeholder. Public User-Agent/Accept headers are preserved for official sources; cookies and authorization are not forwarded. Calendar trials neither receive nor use a Gemini key. All write endpoints still require the independent trial token, and the default flag remains disabled.

Failed news runs can now return only bounded counts and HTTP codes. A monitored PR #113 run reached Google model discovery (HTTP 200), then all six selected generateContent endpoints returned HTTP 503. The trial returned a producer-stage failure, retained its last good state and was disabled afterward. Broad runtime remains unverified; this does not establish a global Google outage or successful source parity.

The first real calendar trial fetched 39 official events with no official-source failures and preserved released values for all 50 matching entries. FRED was configured but its releases/dates call returned HTTP 400; that status alone does not establish whether the key or request parameters were rejected. The proxy now trims surrounding key whitespace and emits only fixed diagnostic categories (key format, rejected key, request parameters, rate limit, unavailable upstream or generic rejection). It reads at most 16 KiB of a provider error and never returns the original message/key. The calendar client accepts only those categories; unknown responses stay generic HTTP errors. No key value, schedule or production data is changed. The new classification still needs an isolated runtime check.


## Isolated non-AI data jobs

The authenticated `/run?job=markets`, `fx`, `economy-history` and `country-basics` selectors run the existing Python generators in disposable directories. Each uses its own Durable Object and `trial/<job>/` R2 prefix, has no schedule, cannot publish and receives no AI, ingest or repository credentials. Country basics and economy history remain review-only artifacts. Markets retains its existing asset universe, failed-asset fallback and half-refresh minimum; ECB keeps the provider reference date, including weekends. No values or financial calculations are rewritten.

Before building, run `python tools/cloudflare/stage_frontend.py <frontend-checkout>`. It stages exactly three scripts and the market registry from pinned frontend commit `2402119767e01574d478e3df72398bba21ffc132` into ignored `.local/cloudflare-frontend/`. It reads committed regular Git blobs, never local configuration or edited working-tree files. Docker includes only those four staging paths. CI uses the existing frontend repository credential for checkout only, with persisted credentials disabled; it never enters the image. Fork PRs cannot access that credential.

Upload a gzip JSON seed to `trial/<job>/seed.json.gz`: markets requires `files.markets.json` from the real frontend snapshot; the other jobs start with `{"files":{}}`. Never submit invented prices. Successful runs retain their own state; failed generators retain the previous good R2 state. Results are available through `/result?job=<job>`. World Bank and Yahoo access is GET-only on their fixed data API paths; source credentials are stripped. Real deployed comparisons, production storage/read adapters and the final coordinated scheduler switch remain required before retiring any GitHub job.

The subsequent calendar retest returned FRED HTTP 200, 39 official events, no official-source failures and zero FRED failures. That establishes that the stored FRED key currently works; it does not establish the earlier rejection's cause or a completed production cutover.


## Full-article storage trial

After a successful news generation, the container exports full articles in bounded pages. The Worker writes them to private `trial/library/articles/<id>.json` objects before advancing its saved producer state. Existing saved articles remain byte-identical, matching the GitHub publisher's first-copy behavior. The large archive remains opaque gzip in the Worker; no R2 or repository credentials enter the container. Only news jobs export articles. A failed export leaves the previous producer state in place; complete individual article objects already written may remain as isolated artifacts and are safe to reuse.

`GET /article?id=<id>` reads one saved full article and requires the same trial bearer token as every other endpoint. Missing/malformed IDs fail closed; this endpoint is not a public website feed. No production API, website URL, scheduler or GitHub publishing workflow changes. Historical static files stay available. Production read routing, library index updates, backfill coverage and website previews remain necessary before retiring the old publishing job.

Real PR #118 trials passed: 951 market assets, 29 ECB currencies (provider date 23 November 2026), 224 country records with zero refresh failures and 243 history files containing 35,452 dated observations. Country basics and history remain review-only. The trial was disabled afterward; these results do not mean the production data schedules have moved.


`POST /run?job=library` copies complete saved articles into the same trial R2 article namespace without fetching sources, generating text or publishing. Seed `trial/library/seed.json.gz` with the validated news-state export. The adapter reuses the existing publisher's `robot_stories` selection unchanged and preserves every article field/date. Its producer-state prefix is separate, but it shares the news Durable Object lock to serialize immutable article writes. It has no Gemini, ingest or repository credentials. This provides an AI-free storage verification/backfill path while generation is unavailable; it does not retire the live GitHub publisher.


Fresh-state news retries on 23 November 2026 remained unsuccessful: priority fetched 226 items (30 candidates, five failed sources) and broad fetched 2,437 items (200 candidates, 19 failed sources). Both reported `gemini_ok=false` and generation HTTP 503, returned a producer-stage failure and retained the last good trial result. This does not establish successful source parity, a global provider outage or a completed news migration. Production GitHub schedules remain in place.


The first real saved-library run failed before writing articles because reusing the producer's Container TCP port handle caused `Network connection lost` on the next fetch. This was reproduced with the real Container API in a fully local Linux development session, without provider keys or cloud storage. Reacquiring the port for each library page resolved it: all 1,501 saved articles transferred to local R2 successfully with zero AI calls. A regression test simulates closed producer/page connections and requires a fresh handle for every page. Temporary exception tracing was removed. The deployed isolated Worker remains disabled; the corrected code still requires an owner merge and Cloudflare runtime verification.


Additional verification: a second local native-Container transfer reported zero article writes; all 1,501 local stored articles matched every original field/date. An independent localhost Worker using the real isolated R2 binding also copied all 1,501 articles, and every actual private R2 readback matched its saved source. This verifies the bucket/artifacts while the deployed Container connection fix is still awaiting owner merge. No production readers or publishing schedules were switched.


## Explicit publication boundary

`PUBLISH_LIBRARY_ENABLED` defaults to `false`. When separately enabled, authenticated `POST /publish-library` copies at most 250 validated full articles from `trial/library/articles/` to `published/library/articles/` per call, preserving exact bytes and every existing published object. The news Durable Object lock serializes this with generation. A listing cursor is checkpointed only after a completed page; partial writes are safe to reuse after failure. Continue until `done:true`. This path starts no Container and calls no AI provider. Trial generation can remain disabled while copying already validated articles.

When the same publication flag is enabled, successful priority/broad generation also writes its exported articles to the published prefix before advancing producer state. Ordinary saved-library trials continue to write only trial artifacts. Neither flag configures a schedule. The website's separate `ARTICLE_STORE` binding and read-only Pages Function accept only the published prefix, keeping seeds, state, trial articles and other private objects inaccessible. Without that binding or when an object is missing, the website retains its static article fallback. No provider key belongs in Pages bindings or browser files.

After PR #120 merged, the deployed Container library transfer and a repeat both passed with zero rewrites; all 1,501 deployed authenticated article readbacks matched their saved source. The trial was confirmed disabled with no schedule afterward. Article listing/index migration, news-provider failures and the coordinated scheduler cutover remain outstanding.


## Safe news-provider diagnostics

Failed Google requests retain the same generic client error and HTTP status, but emit a private `news_provider_failure` console record containing only the HTTP number, an allowlisted provider status and a fixed diagnostic category. Categories help distinguish capacity/unavailability, quota/rate limits, billing restrictions, key rejection, permission/region restrictions, invalid requests and unreadable errors; they are diagnostic hints, not a confirmed cause. Error bodies are read at most 16 KiB and closed. URLs, provider prose, keys, prompts and article contents are never returned or logged. The bounded reader is also reused by FRED, preserving its existing fixed categories and server/rate-limit handling.

During an isolated retry, inspect only these fixed console records; never dump complete request headers or provider bodies. Prompts, models, successful responses, secrets, flags and schedules are unchanged. Actual provider diagnosis still requires a deployed isolated retry after owner merge; this change does not claim that the news 503 failures are fixed.


## Versioned website listings

The separately authenticated `POST /publish-library-index` endpoint uses `PUBLISH_LIBRARY_ENABLED` and the same news lock. It reads **already-published canonical** articles only; it cannot promote trial articles, invoke Gemini, ingest news or change timers. Successful news publication also builds this index before advancing producer state. Generation may remain disabled for an index-only run.

Before building the image, stage a reviewed frontend catalog, independently of the existing pinned data-job scripts:

```text
python tools/cloudflare/stage_frontend.py <frontend-checkout>
python tools/cloudflare/stage_library_index.py <frontend-checkout> --commit <exact-reviewed-40-character-commit>
```

Staging reads only committed regular Git blobs: the original row projection, compact catalog, metadata and ticker shards. The current offline CI baseline is frontend `53b8e93830deab9f574a11745a05e40155fdad2c`. It contains 55,960 articles. No working-tree configs or credentials enter the image. For the coordinated publisher cutover, stage the final static catalog after GitHub publication is paused; an older baseline intentionally cannot replace a newer static archive.

The Container preserves every static row and original ticker link, appends only previously unseen canonical published articles using the original frontend row projection, and produces metadata, search rows and ticker shards. Pagination records exact UTF-8 byte ranges into `all.json`, rather than uploading thousands of page objects. The Worker validates bounds and SHA-256 checksums, saves immutable files under `published/library-index/versions/<sha256>/`, checkpoints compressed private row state, then changes `published/library-index/current.json` **last**. Failed/partial versions remain invisible and can be reused on retry. An unchanged version writes nothing. The 15 MiB catalog is parsed in the 1 GiB Container, not in the Worker.

For this index job only, intercepted `http://article-store/library/<safe-id>.json` requests return exact published objects; `/index-state.json.gz` returns the previous private compact index state. All other origins, paths, methods, query strings and HTTPS requests are denied. This export has no provider keys or forwarded network requests. Cloudflare's [intercept-all DNS behavior](https://developers.cloudflare.com/containers/configuration/outbound-traffic/) resolves the internal hostname without public DNS.

The frontend readers keep the existing `library-index/*` and `site-stats.json` URLs. They activate only when the manifest's baseline hash equals the deployed static catalog's hash. Otherwise they keep the static response. A page reads only its bounded byte range; search retains the existing on-demand full compact index. Homepage project totals stay from the deployed site. Seeds, trial results and compact private state are never exposed.

Offline verification preserved all 55,960 static rows and ticker links and reconstructed every one of 2,332 pages exactly from its byte ranges, with zero model calls. New code still needs owner merge and deployed runtime verification; no schedules or production feed were switched. Current limits are 100,000 rows, 32 MiB per exported file and 512 KiB per page. Versioned objects consume storage over time; review actual R2 storage/container usage before scheduling and add safe retention when needed, without deleting the active version.

Further local verification: the actual generated Python manifest and all 29 index files passed the JavaScript checksum publisher; repeat publication wrote zero files and the public pointer was written last. A real local Cloudflare R2 binding returned exact first/second/final page byte ranges, unchanged full-search bytes and HEAD responses; homepage project totals were preserved. The full 55,960-row generator also ran in a network-disabled, read-only 1 GiB Docker container. These are local checks, not a deployed runtime cutover. The Linux backend suite passed 365 tests (four skips); native Windows runs retain unrelated symlink-permission / project evidence hash failures.
