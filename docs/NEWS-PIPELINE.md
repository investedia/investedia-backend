# News and globe pipeline

This repair is local code only. It has not been deployed, started on a schedule, or used to upload data to Cloudflare. No GitHub configuration is required to run the checks below.

## Flow

Priority RSS/official feeds -> existing Gemini selection -> validated saved news -> globe connections -> authenticated Worker ingestion -> one KV news collection -> /v1/news and /v1/globe.

Home, News and Globe now share `InvNewsSource`: in worker mode it reads /v1/news and merges real API articles with saved articles. Saved files remain the fallback, including their original dates. Static mode makes no API request. Demo data is no longer used as a live-feed fallback.

## Check without running anything live

From the backend root:

```powershell
python tools/news-pipeline.py
python tools/push-news-to-worker.py --check
node --test workers/live/test/*.test.mjs
node tests/news-ingest.integration.mjs
python -m unittest discover -s tests -p test_ingestion_recovery.py
python -m unittest discover -s tests -p test_push_news_worker.py
```

The first command is a read-only preflight. It reports missing setting **names**, not secret values. The integration test uses loopback HTTP, the real saved articles, an ephemeral KV/cache and a temporary test correction. It does not call Cloudflare, generate articles, or modify source feeds.

## Run explicitly after credentials and target are confirmed

Required environment variables: GEMINI_API_KEY, WORKER_URL, NEWS_INGEST_TOKEN. The uploader token must match the Worker's INGEST_TOKEN secret. PIXABAY_KEY and Pillow are optional for topic-photo generation. `.env.example` lists names; scripts read the process environment and do not automatically load a .env file. Never put these secret values in frontend configuration or Git.

```powershell
python tools/news-pipeline.py --run
```

This is an explicit live-provider/upload operation: do not execute it during a dry run. It runs **priority news only** with bounded subprocess timeouts and a local overlap lock; it removes inherited backfill settings. It checks recorded generator success because the legacy generator can exit zero after errors, generates globe connections, and requires acknowledged Worker ingestion. Generation logs stay ignored under `.local/`.

Production news reaches the website through `/v1/news` and `/v1/globe`, using `dataMode=worker` and the approved API base URL. No frontend file commits, delivery PRs, Pages builds or deploys are needed per news update. Existing saved frontend feeds remain an honestly dated fallback.

The inactive deployment template schedules at most hourly, allows one concurrent run and caps each job at two minutes. Slow provider runs can time out and must be reported as failures. See `DEPLOYMENT-PREPARATION.md` for the private Actions minutes budget and separate enablement approval. It provides no Pixabay key, so it selects only from saved photo pools. Verify selected photo paths already exist on the deployed site; the API does not deliver local image bytes. A future new-photo hosting path needs separate approval without automated frontend commits/builds.

The pre-existing optional `--frontend PATH` argument remains available for explicit manual recovery/export only; the scheduler never uses it. The runner never invokes V5, financial engines, Git operations or deployment commands. No scheduler is activated by this preparation.

## Failure and freshness guarantees

- Missing required settings and failed uploads exit nonzero; missing settings can only be skipped with the uploader's explicit `--optional` flag.
- Tokens travel in Authorization headers, not URLs. Embedded URL credentials/query tokens and unsafe external HTTP targets are rejected. Redirects are refused so credentials cannot be forwarded to another destination.
- Worker ingestion retains source generation time, rejects invalid/future timestamps and invalid coordinates, and refuses an older feed over a newer one.
- Same-ID editorial corrections are written; an unchanged feed is not rewritten. A malformed stored collection can be restored with a valid authenticated feed.
- Successful changes invalidate the normal news/globe edge-cache entries. Both endpoints derive their contents from the same saved collection.
- Upload time is stored separately and never used to make old articles appear freshly generated. Previously saved article publication dates and financial ledgers are unchanged.
- API failures/invalid records never replace a valid saved frontend feed with an empty list. No fake/demo articles are silently substituted.

## Still external

The existing hosted news/globe routes will continue returning their previous result until the repaired Worker code/configuration is deployed to the intended account and a valid producer actually ingests news. This local repair cannot prove hosted KV bindings, provider billing/quotas or matching hosted secrets without account access. A fresh-provider run and staged readback are still required before a production claim. The November 8 saved feed was used only for local tests and was not uploaded as new news.
