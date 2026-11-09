# Investedia backend

A standalone services repository recovered from the Java backend branch `a9dec4566927137e2232a6a06dc0a644f7138dd7`. No frontend checkout, old GitHub account or Git remote is required to build or test it.

## Layout

- `api/`: Java 21 / Spring Boot 4.1.2 read-only saved-data API.
- `workers/live/`: preserved Cloudflare Worker, its providers and contract tests. Recovered config has no active crons; GitHub dispatch requires explicit new configuration and opt-in, never the former account by default.
- `assets/`, `data/`: original saved/public snapshots and source datasets used by the API and jobs.
- Root Python scripts and `tools/`: preserved update/ingestion jobs; not scheduled or run by this recovery.
- `engine/`, `research/`: preserved frozen/historical work. V5 and Track Record are not modified; V7 remains research-only.
- `emails/`: existing auth/email setup reference files, not automatically applied.

## Build and run

Use Java 21, Maven 3.6.3+ and Node 20+ (Node is used by Java/Worker contract tests). On Windows, `mvnw.cmd` is a small launcher that finds installed Maven and Java, including this machine's IntelliJ Maven and Corretto JDK. It does not download or install a Maven distribution. On other systems use `mvn` on PATH.

```powershell
.\mvnw.cmd verify
cd api
java -jar target/investedia-backend-0.1.0-SNAPSHOT.jar
```

If Java is not on PATH, use the workspace `Start Local.ps1`, which discovers the installed JDK. Default API: http://127.0.0.1:8080/. Run the JAR from **api/**, or set `INVESTEDIA_REPOSITORY_ROOT` to the absolute backend repository root. Optional `PORT` and `BACKEND_BIND_ADDRESS` exist; keep the loopback bind for local use.

The Maven reactor packages the API; no cloud credentials are needed. Dependencies use normal Maven storage. The recovery verification reused an existing local Maven cache, now retained under the workspace archive; a fresh machine may need internet access to download dependencies.

## API scope

Health, `/v1/prices`, `/v1/news`, `/v1/globe`, `/v1/calls` and `/v1/status` work using the saved data within this repository. Responses report `X-Inv-Source: repository-snapshot`; original financial/provider timestamps are preserved. Ledger bytes are served exactly with ETag and conditional 304 support. Status reports unknown KV/cron metrics as null.

This Java server is not a complete replacement for the old hosted Worker. `/ticker` and ingestion POSTs deliberately return 503. Live providers, authenticated writes and durable ingestion need a separate migration; no fake live feed was added. Supabase remains the account service, consumed directly by the frontend with its public key. This API does not claim to validate Supabase sessions or manage accounts.

## Tests

```powershell
.\mvnw.cmd verify
node --test workers/live/test/*.test.mjs
node api/tools/export-symbol-groups.mjs --check
```

Fresh recovery results: 13 Java tests pass and the executable JAR packages; 33 Worker tests pass. Contract fixtures are included locally. Original `api/VERIFICATION.md` and migration notes are historical documents; the workspace `recovery/VERIFICATION.md` records the current split validation. Existing broader Python/financial tests are preserved but are not asserted fully green; some inherited tests still expect the monorepo layout or have documented baseline failures. Do not run jobs just to make a test pass or rewrite financial history.

## Credentials and deployment

No GitHub remotes/actions were added. No Cloudflare deployment, Supabase settings/schema update or scheduled job was performed. `.env.example` documents optional future provider settings; real `.env`, `.dev.vars`, logs and runtime caches are ignored. Never expose backend secret keys in frontend configuration. Public website data must remain honestly timestamped. **Not investment advice.**
