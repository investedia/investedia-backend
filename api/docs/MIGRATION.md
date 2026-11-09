# Local Java / Spring backend migration

This optional Java 21 / Spring Boot API uses controller, service and repository layers. It reads existing saved snapshots. Production continues using the Worker; Supabase continues providing authentication/accounts. No hosting, identity, payment or frontend endpoint is switched.

## Architecture and data map

Controllers call services; services use repository interfaces; file adapters read existing snapshots. Automated architecture tests enforce dependency direction and reject cycles. No ORM, schema migration or new financial dataset is introduced.

- Prices: assets/quotes.js values and original saved/provider timestamps. These are saved prices, not a live feed. Not investment advice.
- News/globe: assets/globe/news-live.json, selecting the tested Worker-compatible newest-40 ordering and retaining the source fields.
- Calls: exact assets/globe/v5-ledger.json bytes with a representation ETag and conditional 304. No prediction computation, activation, modification or ledger write.
- Status: real snapshot timestamps/counts; unknown Cloudflare KV/cron/limits are null. The application explicitly identifies read-only snapshot mode.

The server binds to loopback by default. Existing robots, schedules, models, historical financial results, auth/accounts, Stripe and production configuration are unchanged.

## Contracts and verification

Use the [numbered task and criteria table](../../design/CODEX-TASK-JAVA-BACKEND.md), [module instructions](../README.md), [verification guide](../VERIFICATION.md) and single [sanitized author-run Maven transcript](../evidence/maven-verify.log). All acceptance evidence linked here is in this repository; no claim depends on private smoke scripts, local cache directories or another PR's reports.

`mvn verify` from backend/ requires Java 21, Maven, Node 20+ and this checkout's workers/live/v1/ modules plus the saved input files. It verifies packaging, local HTTP startup, architecture boundaries, repository behavior and tested Worker read contracts. The contract test checks that Spring and Node use the same fixed instant.

For /v1/calls, missing/unreadable/out-of-root/corrupt ledgers map to the documented Worker-compatible 404. Other snapshot reads fail unavailable with their existing 503 envelopes. The 404 does not distinguish corruption from an empty source; malformed-ledger regression tests use only temporary files. Internal paths are not returned to clients.

Backend documentation/evidence lives under backend/ and design/, outside docs/, which is the GitHub Pages root. No frontend screenshots or browser validation is claimed for this API-only PR.

## Not done

This is a local read-only prototype, not a complete production Worker replacement. Live crypto, ingestion/writes, durable storage, production JWT/account endpoints, complete method/header/error parity, edge caching and deployment remain deferred. Production cutover and any data/schema/auth changes require a separate owner instruction. No merge or deployment is authorized or performed.
