# Backend news cleanup

Local branch: `codex/backend-lean-news`. Baseline: `6229335`.

## Results

- News and globe reads: after validating the current feed, read optional history and connection metadata together. Three sequential storage-wait stages become two; total reads remain three. Missing or corrupt optional values remain independent failures, and an invalid current feed still stops after one read.
- Unchanged library uploads: reuse metadata already read. Total storage reads fall from three to two; metadata reads fall from two to one; writes remain zero. Missing metadata initialization also avoids a second successful read. The existing retry after a failed initial metadata read is preserved.
- Removed the duplicate Java `stats` metadata assignment and its redundant comment.
- No dependencies, caches, endpoints, auth, schema or financial-job changes. Three source files have seven lines added and seven removed overall.

## Files changed

- `workers/live/v1/news.js`
- `workers/live/v1/library.js`
- `api/src/main/java/com/investedia/backend/service/NewsService.java`
- `workers/live/test/read-efficiency.test.mjs`: nine new checks for concurrent reads, optional-storage failures, invalid feeds, read counts, zero-write behavior and retry preservation.
- This review report.

## Validation

- Baseline: all 92 Worker tests and `mvnw.cmd verify` passed.
- Final: all 101 Worker tests passed.
- Final: `mvnw.cmd -B -ntp verify` passed, including all 13 Java tests, architecture rules, local startup, repository failure handling and API-to-Worker response contracts.
- Nine additional complete response comparisons against baseline `6229335` passed with the real saved news feed and combinations of missing, malformed and valid optional data.
- `git diff --check` passed.
- No tracked changes to `assets/`, `data/` or `supabase/`. Existing untracked Graphify files remain untouched. Article timestamps and financial ledgers are unchanged.

No pre-existing or new failing checks. The Java compiler still reports existing deprecated API usage. Timing gains depend on actual storage latency; the checks prove reduced waits and reads, not production milliseconds.

Nothing pushed or deployed. No external financial jobs, real storage writes or messages were sent. Live provider availability and production performance were not tested. This is a targeted news/library cleanup, not a rewrite of the whole backend.
