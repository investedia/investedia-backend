# Owner settings for hourly priority news

No secret values belong in this document, repository, PR text or browser config.

| Store | Exact name | Purpose |
|---|---|---|
| Backend GitHub Actions secret | `GEMINI_API_KEY` | Existing Gemini key for priority article selection |
| Backend GitHub Actions secret | `WORKER_URL` | Exact approved HTTPS Worker base URL (without endpoint suffix); stored as requested in Secrets |
| Backend GitHub Actions secret | `NEWS_INGEST_TOKEN` | Upload authentication; securely match the Worker value below |
| Cloudflare Worker secret | `INGEST_TOKEN` | Same value as `NEWS_INGEST_TOKEN`, checked by ingestion |
| Backend GitHub Actions variable | `PRIORITY_NEWS_ENABLED` | Keep unset/false until owner approval; set `true` only for approved operation |

No frontend write token, GitHub delivery App, deployment token, Supabase service-role key or V5/V7 secret is needed by the scheduled job. Do not supply `PIXABAY_KEY` yet: new-photo delivery is only proposed. `PRICES` is the existing KV binding, not a secret; its owner-supplied namespace ID is already in wrangler.toml without angle brackets.

The workflow uses an hourly UTC cron, one concurrency group, read-only repository contents permission, a 15-minute timeout and explicit failure reporting. It only generates priority news and calls the Worker ingestion API. It never commits into the frontend or triggers a Pages build. The Worker itself has only the two-minute price cron; news and legacy dispatch stay off in Worker vars.

A full 15-minute run each hour would exceed the private-repository free Actions allowance. Review actual duration, billing alerts and spending limits before enabling; use a lower cadence if needed. No billing or secret-store settings are changed by this branch.
