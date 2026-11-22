# Isolated priority-news trial

This is preparation only. It does not deploy, generate news during CI, change the live Worker, publish articles, send alerts, or disable GitHub jobs. Owner approval is required before creating resources, adding secrets, deploying, or enabling generation.

The older `workers/live/v1/news.js` prototype is not equivalent to the Python producer: its sources, IDs, retention, archive and connection handling differ. This container runs the current `update_globe_news.py` priority tier and `tools/globe-news/connections.py` unchanged. The usual `tools/news-pipeline.py --run` wrapper is deliberately excluded because it also ingests into production.

## Isolation

- Separate Worker `investedia-news-trial`, Durable Object and private R2 bucket of the same name. No production routes, KV, Supabase, ingest token, alert credentials or publishing scripts.
- `TRIAL_ENABLED = "false"` and no cron triggers. Every public endpoint requires a separate `TRIAL_TOKEN` secret, including health/results. The HTTP API accepts no input files, URLs, environment or commands.
- Container Internet access is disabled. HTTPS interception permits GETs only to exact priority-source hosts, plus Gemini model listing/generation. Redirects are checked again; production destinations, bare IPs and other writes are denied. The real Gemini key stays in the Worker and is injected only into Gemini requests; the Python process gets a proxy placeholder.
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
| GET | `/result` | Last successful gzip-compressed JSON artifact: full trial files, connections and measured summary |

Send `Authorization: Bearer <trial token>` securely; do not place the token in the URL or terminal history. `/run` waits for the producer, so use a client with a sufficiently long timeout. A failed request is not automatically retried. `trial/state.json.gz` resumes the trial's own seen/archive state on later runs; production continues independently. To restart from a fresh seed, remove only the trial state object after reviewing/saving the old artifact.

## What remains to prove

Docker/runtime checks, HTTPS interception/certificate support and real-source redirect behavior must pass in the deployed isolated environment before any comparison is trusted. Source descriptions hosted outside the exact source allowlist are blocked; the producer retains its normal description fallback. Review failed-source diagnostics and extend only specific verified publisher hosts if needed. No Pixabay downloads are allowed; existing photo references are reused just as in the priority GitHub workflow. The container does not serve photo files or a website preview.

This is a manual first trial, not the completed 24-hour comparison or a replacement scheduler. Before a production switch, compare source failures, new article IDs/counts, countries/regions, archive/library, photo references, connections, errors and duration over representative runs. Show website previews when wiring any alternative feed. Only after a successful comparison and a separate owner approval may production ingestion or schedules change. This PR makes neither change.

The real producer state can exceed 32 MiB uncompressed. Seeds/results now use gzip without trimming articles, events or timestamps. The Worker stores opaque compressed bytes and parses only a small summary header; the container enforces both compressed and expanded size bounds. Legacy raw JSON seeds remain readable. The container uses the `basic` (1 GiB) instance to accommodate parsing the archive, and still stops after every run. This uses more resources than the old `lite` setting; actual trial cost and peak memory must be measured before scheduling. The trial still has no automatic schedule or production credentials.
