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
python tools/news-pipeline.py --run --frontend ../frontend
```

This is an explicit live-provider/upload operation: do not execute it during a dry run. It runs **priority news only** with bounded timeouts and a local overlap lock; it removes any inherited backfill setting. It checks the generator's recorded success because the legacy generator can exit zero after errors. It then generates globe connections, ingests, exports saved JSON and new photo assets, and rebuilds the chosen frontend. The frontend path is validated before any generation or upload. Generation logs are ignored under `.local/`. The optional export is necessary when new article photos use local file URLs; an API response alone cannot deliver those image files to a static host.

Without `--frontend`, only the backend feed/connections and Worker are updated. Export and deploy the frontend's actual photos/feed separately before claiming the public website is current. The runner never runs V5, financial engines, Git operations or deployment commands. No scheduler/self-chaining is installed. A future scheduler can invoke this bounded job once per run after its account and secret stores are chosen.

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
