# Graph Report - investedia-published-library-19mbzk6_  (2026-11-23)

## Corpus Check
- 8199 files · ~1,939,847 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 5, .csv 3, .otf 3)

## Summary
- 3417 nodes · 6406 edges · 238 communities (153 shown, 85 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 153 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3c617ce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Outcome
- calendar_fred.py
- pathlib
- regional-backfill.py
- json
- update
- MarketsPilotTests
- SnapshotRepositoryTest.java
- ApiContractTest.java
- connections.js
- live/index.js
- prices.js
- registry.py
- with
- steps
- steps
- steps
- MarketService
- steps
- with
- steps
- v1/news.js
- worker-contracts.mjs
- with
- steps
- update_share_cards.py
- news-gap-backfill.py
- update_globe_news.py
- steps
- steps
- calendar_official.py
- hashlib
- NewsService.java
- markets_audit/run.py
- news_core.py
- SnapshotResponseHeaders.java
- fetch.py
- markets.js
- test_projects_media.py
- update_market.py
- FileMarketRepository.java
- ref_node_assert
- regional-backfill.test.mjs
- gdelt-backfill.py
- alerts.js
- with
- NewsImpacts
- featured
- NewsPhotos
- with
- .missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths
- math
- env
- AzureEditorTests
- news-trial/library.test.mjs
- newscore.js
- with
- news.test.mjs
- with
- LicensingEvidenceTests
- server
- time
- inputs
- judge_daily
- test_news_core.py
- news-gap-backfill.yml
- steps
- runner.py
- README.md
- regional-backfill.yml
- Policy
- StrictNewsTests
- fx_audit
- parse_gkg
- Prediction Engine v4: design and frozen rules
- ApiConfiguration.java
- test_projects_pipeline.py
- inputs
- with
- with
- audit.py
- balance
- source_licensing.py
- ClaudeEditor
- Clock
- events.py
- steps
- LiveConnectionsTests
- EndToEndTests
- MarketFocusTest
- package.json
- steps
- ExchangeCoordinatesTest
- env
- country_basics.py
- RegionalFixTests
- InvestediaApplication.java
- env
- MarketTests
- GapTests
- RecoveryIntegrationTests
- SectorTests
- with
- confirm
- start
- batch_size
- tabular
- dry_run
- gemini_calls
- SavedFeeds
- BasicsTests
- FeedsTests
- StageIntegrationTests
- PushNews
- re
- calendar_fred.py
- sources
- com.investedia:investedia-backend
- com.investedia:investedia-services
- with
- steps
- os
- thin-recent.yml
- alert-email-preview.yml
- test_projects_scale.py
- env
- copy
- RegionalTests
- context.py
- Identity
- ProjectsPipelineTests
- enrich_page
- ClaudeProviderTests
- markets_pilot/registry.py
- batch_size
- org.springframework.web.bind.annotation.GetMapping
- connections.test.mjs
- ingest
- backfill-photos.py
- methods.py
- Downloads
- gkg_zip
- generate
- with
- steps
- AuditInputTests
- PublishLibrary
- exchange_hours.py
- enrich_page
- inputs
- CalendarTrialTests
- re
- DiscoveryTests
- Projects scale — stage 1, 11 November 2026
- .test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files
- writer
- sources
- writer
- call
- ClaudeWriterTests
- error_message
- WindowsAndRegions
- country_cap
- parse_time
- end_date
- gdelt_files
- test_markets_pilot.py
- update_asset_analysis.py
- regions
- start_date
- connections_only
- ConnectionTests
- DataTrialTests
- Regional article and connection recovery
- NewsTrialTests
- P19 Part A · draft ingestion foundation, expanded coverage blocked
- US / UK Markets pilot — artifact and API code only
- HoursTests
- Isolated priority-news trial
- Country coverage audit
- Projects media — stage 2 preparation
- TrialExportTests
- AuditTests
- Deployment preparation — inactive proposal
- LegalLinks
- LegacyRetryBudgetTests
- One-off outage recovery — staging only
- ingest
- PhotoPoolTests
- dry_run
- Live Globe connections — draft delivery fix
- Backend news cleanup
- Prediction Engine v5 candidate: FROZEN before the held-out test
- Investedia backend
- gemini_calls
- Markets coverage feasibility
- Proposed identity model — no registry built
- manifest.json
- Projects scale — stage 3 partial source pass
- Early calls: scoring framework v2 (frozen before scoring)
- Feed coverage inventory
- Primary source licensing evidence
- Markets coverage preparation
- Source licensing audit — phase 01
- Budget
- max_usd
- CLAUDE.md
- country-basics.md
- API.md
- FX.md
- OWNERSHIP.md
- PIPELINE.md
- RUN.md
- SCHEMAS.md
- SEC.md
- library-publish-retry/REPORT.md
- retired-prs/REPORT.md
- LIVE-OUTCOME-RULES.md
- projects-scale/README.md
- share/README.md
- PHOTO-DELIVERY.md
- PRODUCTION-SETTINGS.md
- Threads
- FredTrialErrorTests
- Extraction
- OldGkgWithoutPageTitle
- RecentIngestTests
- CachedRepresentationTests

## God Nodes (most connected - your core abstractions)
1. `run()` - 37 edges
2. `MarketsPilotTests` - 31 edges
3. `run()` - 30 edges
4. `fetch()` - 29 edges
5. `env` - 23 edges
6. `build()` - 22 edges
7. `ProjectsPipelineTests` - 21 edges
8. `reconcile()` - 20 edges
9. `main()` - 19 edges
10. `Prediction Engine v4: design and frozen rules` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Full-article storage trial` --references--> `robot_stories()`  [INFERRED]
  workers/news-trial/README.md → tools/publish_library.py
- `1. Audit of the current live engine (Prediction Engine v2, `impact-gemini-v2`)` --references--> `dedupe()`  [INFERRED]
  research/ENGINE-V4.md → news_core.py
- `Source and evidence rules` --references--> `backfill_impacts()`  [INFERRED]
  data/coverage/BACKFILL.md → update_globe_news.py
- `Source and evidence rules` --references--> `pick_stories()`  [INFERRED]
  data/coverage/BACKFILL.md → update_globe_news.py
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py

## Import Cycles
- None detected.

## Communities (238 total, 85 thin omitted)

### Community 0 - "Outcome"
Cohesion: 0.29
Nodes (3): Context, Outcome, session()

### Community 1 - "calendar_fred.py"
Cohesion: 0.10
Nodes (15): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), release_events(), Base (+7 more)

### Community 2 - "pathlib"
Cohesion: 0.05
Nodes (11): jpeg(), AzureProviderAccepted, CommandLineTests, CountryCapTests, http_error(), RecentWindowTests, TitleJunkTests, HistoryConnections (+3 more)

### Community 3 - "regional-backfill.py"
Cohesion: 0.10
Nodes (31): content_hash(), archive(), batches(), cached_patch(), contains_secret(), dedupe(), draw_connections(), english_headlines() (+23 more)

### Community 4 - "json"
Cohesion: 0.06
Nodes (28): stage(), facts(), load(), main(), parse(), get(), main(), backfill() (+20 more)

### Community 5 - "update"
Cohesion: 0.11
Nodes (15): Ledger, story(), Track, bench_of(), call_start(), freeze(), judge(), load() (+7 more)

### Community 6 - "MarketsPilotTests"
Cohesion: 0.13
Nodes (6): MarketsPilotTests, build(), fx_relationships(), reconcile(), find(), union()

### Community 7 - "SnapshotRepositoryTest.java"
Cohesion: 0.10
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "ApiContractTest.java"
Cohesion: 0.06
Nodes (4): ApiContractTest, TimeConfiguration, LayeredArchitectureTest, LocalStartupTest

### Community 9 - "connections.js"
Cohesion: 0.15
Nodes (18): now, clean(), distance(), ingestConnections(), MAX_BODY, MAX_ROWS, MAX_STORED, point() (+10 more)

### Community 10 - "live/index.js"
Cohesion: 0.10
Nodes (24): ALIAS, ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), withAliases() (+16 more)

### Community 11 - "prices.js"
Cohesion: 0.13
Nodes (31): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, NOW, day() (+23 more)

### Community 12 - "registry.py"
Cohesion: 0.08
Nodes (16): call_of(), main(), context_of(), series(), v5(), ascii_lower(), get(), name_key() (+8 more)

### Community 13 - "with"
Cohesion: 0.06
Nodes (34): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, DOWNLOAD_MB, max_download_mb (+26 more)

### Community 14 - "steps"
Cohesion: 0.06
Nodes (33): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, GEMINI_API_KEY (+25 more)

### Community 15 - "steps"
Cohesion: 0.06
Nodes (33): concurrency, cancel-in-progress, group, GEMINI_API_KEY, NEWS_INGEST_TOKEN, PIXABAY_KEY, WORKER_URL, jobs (+25 more)

### Community 16 - "steps"
Cohesion: 0.06
Nodes (31): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, SAMPLE_LIMIT, sample_limit (+23 more)

### Community 17 - "MarketService"
Cohesion: 0.19
Nodes (4): MarketController, MarketRepository, MarketService, SnapshotMetadata

### Community 18 - "steps"
Cohesion: 0.06
Nodes (30): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, CALENDAR_UNLICENSED (+22 more)

### Community 19 - "with"
Cohesion: 0.08
Nodes (29): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, java (+21 more)

### Community 20 - "steps"
Cohesion: 0.07
Nodes (28): concurrency, cancel-in-progress, group, default, description, runs-on, steps, timeout-minutes (+20 more)

### Community 21 - "v1/news.js"
Cohesion: 0.07
Nodes (32): generate(), feed, feed, canonicalValue(), CONNECTION_FIELDS, DIRS, emptyNewsStats(), fnv() (+24 more)

### Community 22 - "worker-contracts.mjs"
Cohesion: 0.07
Nodes (18): target, env, expected, feed, now, p, quotes, snapshots (+10 more)

### Community 23 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, deploy (+19 more)

### Community 24 - "steps"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, notices, name (+19 more)

### Community 25 - "update_share_cards.py"
Cohesion: 0.14
Nodes (16): ShareCards, ago_text(), caption(), draw_logo(), load(), move_since(), page(), parse() (+8 more)

### Community 26 - "news-gap-backfill.py"
Cohesion: 0.13
Nodes (19): articles(), ArticleText, confirm(), dedupe(), digest(), get(), in_window(), keys() (+11 more)

### Community 27 - "update_globe_news.py"
Cohesion: 0.14
Nodes (20): Source and evidence rules, atomic_write(), backfill_impacts(), compact48(), describe(), err(), gdelt(), gemini() (+12 more)

### Community 28 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 30 - "calendar_official.py"
Cohesion: 0.28
Nodes (8): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar

### Community 31 - "hashlib"
Cohesion: 0.08
Nodes (18): DiscoveryTests, ScaleTransportTests, commons_candidate(), discover(), main(), query(), text(), run() (+10 more)

### Community 32 - "NewsService.java"
Cohesion: 0.17
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "markets_audit/run.py"
Cohesion: 0.11
Nodes (18): AuditScopeTests, RunnerBoundaryTests, configured(), dates(), get(), main(), NoRedirect, probe() (+10 more)

### Community 34 - "news_core.py"
Cohesion: 0.11
Nodes (14): age_minutes(), authority_of(), canon(), dedupe(), entities(), freshness(), from_iso(), jaccard() (+6 more)

### Community 35 - "SnapshotResponseHeaders.java"
Cohesion: 0.14
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "fetch.py"
Cohesion: 0.16
Nodes (12): collect(), companies_house(), confirmed_ogl(), gleif(), golden_urls(), walk(), local(), sec_directory() (+4 more)

### Community 37 - "markets.js"
Cohesion: 0.25
Nodes (16): setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer(), metadata() (+8 more)

### Community 38 - "test_projects_media.py"
Cohesion: 0.16
Nodes (7): MediaTests, attach(), contained(), date(), https(), sha(), validate()

### Community 39 - "update_market.py"
Cohesion: 0.21
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "ref_node_assert"
Cohesion: 0.14
Nodes (13): fixture, article(), gap(), now, req(), seed(), cleanName(), handleGreeting() (+5 more)

### Community 42 - "regional-backfill.test.mjs"
Cohesion: 0.36
Nodes (8): article(), backfilled(), body(), impact, iso(), NOW, post(), seed()

### Community 43 - "gdelt-backfill.py"
Cohesion: 0.07
Nodes (38): country_allowed(), day(), dedupe(), generate(), gkg_plan(), headline_key(), ingest_artifact(), acknowledged() (+30 more)

### Community 44 - "alerts.js"
Cohesion: 0.11
Nodes (39): RFC-8291, RFC-8292, te, about(), channelsFor(), country(), COUNTRY_ALIAS, deliver() (+31 more)

### Community 45 - "with"
Cohesion: 0.08
Nodes (23): jobs, offline-trial, name, if, runs-on, steps, timeout-minutes, on (+15 more)

### Community 47 - "featured"
Cohesion: 0.05
Nodes (42): featured, country, description, figures, id, lat, location, lon (+34 more)

### Community 49 - "with"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, if, runs-on, steps, timeout-minutes, jobs (+22 more)

### Community 50 - ".missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths"
Cohesion: 0.16
Nodes (5): CallController, LedgerDocument, CallRepository, CallService, SnapshotRepositoryTest

### Community 51 - "math"
Cohesion: 0.18
Nodes (10): expected(), meaningful(), correlation(), dated(), ecb_rates(), exchange_connections(), fetch(), main() (+2 more)

### Community 52 - "env"
Cohesion: 0.11
Nodes (18): ANTHROPIC_API_KEY, BACKFILL_BATCH_INPUT, BACKFILL_CALLS_INPUT, BACKFILL_CONFIRM_INPUT, BACKFILL_CONNECTIONS_INPUT, BACKFILL_DAYS_INPUT, BACKFILL_DRY_RUN_INPUT, BACKFILL_SOURCES_INPUT (+10 more)

### Community 54 - "news-trial/library.test.mjs"
Cohesion: 0.13
Nodes (20): NewsTrial, TrialEgress, boundedJson(), publishLibraryPage(), publishSavedArticle(), readTrialArticle(), storeTrialLibrary(), rows (+12 more)

### Community 55 - "newscore.js"
Cohesion: 0.13
Nodes (23): Data API v1 (prices, status; news and globe come next), Deploy (about 15 minutes, free plan), Investedia live relay (Cloudflare Worker), Limits and safety, News and globe (built, benchmarked, NOT the primary path), NOW, V, refreshNews() (+15 more)

### Community 56 - "with"
Cohesion: 0.05
Nodes (40): default, description, concurrency, cancel-in-progress, group, GH_TOKEN, backfill_run, jobs (+32 more)

### Community 57 - "news.test.mjs"
Cohesion: 0.20
Nodes (11): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), geminiRows(), genOk(), NOW (+3 more)

### Community 58 - "with"
Cohesion: 0.05
Nodes (37): runs-on, steps, timeout-minutes, default, description, type, concurrency, cancel-in-progress (+29 more)

### Community 60 - "server"
Cohesion: 0.17
Nodes (11): name, include-message, include-stacktrace, investedia, repository-root, server, address, error (+3 more)

### Community 61 - "time"
Cohesion: 0.07
Nodes (23): ok(), fetch(), NoRedirect, sparql(), get(), get(), fetch(), main() (+15 more)

### Community 62 - "inputs"
Cohesion: 0.13
Nodes (15): description, required, default, description, required, default, description, confirm (+7 more)

### Community 63 - "judge_daily"
Cohesion: 0.31
Nodes (3): Daily, day(), judge_daily()

### Community 64 - "test_news_core.py"
Cohesion: 0.18
Nodes (7): iso(), retain(), validate_feed(), cand(), Core, story(), load_seen()

### Community 65 - "news-gap-backfill.yml"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "steps"
Cohesion: 0.17
Nodes (12): if, runs-on, steps, timeout-minutes, jobs, backfill, id, if (+4 more)

### Community 67 - "runner.py"
Cohesion: 0.15
Nodes (14): allowed(), decode_bundle(), encode_bundle(), GenerationFailed, Handler, library_page(), pack(), run() (+6 more)

### Community 68 - "README.md"
Cohesion: 0.09
Nodes (17): Architecture and data map, Contracts and verification, Local Java / Spring backend migration, Not done, Independent backend verification, Not done, Check without running anything live, Failure and freshness guarantees (+9 more)

### Community 69 - "regional-backfill.yml"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, name, on, workflow_dispatch, permissions, actions (+1 more)

### Community 72 - "fx_audit"
Cohesion: 0.38
Nodes (4): FXTests, fx_audit(), pearson(), returns()

### Community 74 - "Prediction Engine v4: design and frozen rules"
Cohesion: 0.11
Nodes (18): 10. Outcome rule outcome-v4 (for v4 calls), 11. Evaluation (no tuning on the holdout), 11a. Track Record datasets, 11b. Expected volume (archive proxy, 22–30 Oct; development estimate, not a target), 12. Data, 13. Known risks, 2. Architecture of v4 (shadow first, then promotion), 2a. Products (one engine, three outputs; never blurred) (+10 more)

### Community 76 - "test_projects_pipeline.py"
Cohesion: 0.22
Nodes (10): history(), km(), load(), main(), _rules(), candidates(), connections(), fingerprint() (+2 more)

### Community 77 - "inputs"
Cohesion: 0.22
Nodes (9): default, description, required, end, review_json, staging_run_id, description, description (+1 more)

### Community 78 - "with"
Cohesion: 0.22
Nodes (9): with, github-token, if-no-files-found, name, path, persist-credentials, python-version, retention-days (+1 more)

### Community 79 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 80 - "audit.py"
Cohesion: 0.30
Nodes (11): assets_for(), date(), fetch_api(), finite(), generate(), main(), markdown(), NoRedirect (+3 more)

### Community 81 - "balance"
Cohesion: 0.39
Nodes (3): Balance, c(), balance()

### Community 82 - "source_licensing.py"
Cohesion: 0.23
Nodes (9): active_sources(), collect(), checked_fetch(), contains_secret(), get(), main(), cached_fetch(), NoRedirect (+1 more)

### Community 83 - "ClaudeEditor"
Cohesion: 0.11
Nodes (6): AzureEditor, ClaudeEditor, BudgetExceeded, ClaudeWriter, ModelBudget, ModelUnavailable

### Community 84 - "Clock"
Cohesion: 0.19
Nodes (5): Clock, get(), PublisherPageTests, redirecting(), get()

### Community 85 - "events.py"
Cohesion: 0.12
Nodes (13): save(), family(), load_days(), record(), _t(), threads(), upsert(), _write() (+5 more)

### Community 86 - "steps"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 90 - "package.json"
Cohesion: 0.25
Nodes (7): name, private, scripts, bench, bench:news, test, type

### Community 91 - "steps"
Cohesion: 0.06
Nodes (33): description, required, PER_TOPIC, PIXABAY_KEY, confirm, per_topic, jobs, photos (+25 more)

### Community 93 - "env"
Cohesion: 0.06
Nodes (32): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, MAX_TOTAL, QUEUE, SPENT (+24 more)

### Community 94 - "country_basics.py"
Cohesion: 0.33
Nodes (8): apply_indicator(), get(), main(), NoRedirect, numeric(), observation(), read(), saved()

### Community 97 - "env"
Cohesion: 0.33
Nodes (6): GAP_END, GAP_START, NEWS_INGEST_TOKEN, REVIEW_JSON, WORKER_URL, env

### Community 102 - "with"
Cohesion: 0.06
Nodes (30): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, default, description (+22 more)

### Community 103 - "confirm"
Cohesion: 0.50
Nodes (4): default, description, type, confirm

### Community 104 - "start"
Cohesion: 0.50
Nodes (4): start, default, description, required

### Community 105 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 106 - "tabular"
Cohesion: 0.10
Nodes (10): TabularScaleTests, records(), tabular(), parse(), parse(), parse(), parse(), parse() (+2 more)

### Community 107 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 114 - "re"
Cohesion: 0.14
Nodes (18): build(), canonical(), company_links(), covered(), digest(), distance(), featured(), finite() (+10 more)

### Community 115 - "calendar_fred.py"
Cohesion: 0.24
Nodes (3): FredError, _get(), _obs()

### Community 116 - "sources"
Cohesion: 0.40
Nodes (5): sources, default, description, options, type

### Community 121 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, jobs, refresh, name, on, schedule (+19 more)

### Community 122 - "steps"
Cohesion: 0.08
Nodes (25): ANTHROPIC_API_KEY, MAX_USD, runs-on, steps, timeout-minutes, max_usd, jobs, fill (+17 more)

### Community 123 - "os"
Cohesion: 0.06
Nodes (19): build_prompt(), calendar_expectations(), story_block(), exit_bar(), judge(), move_between(), _sessions(), decide() (+11 more)

### Community 124 - "thin-recent.yml"
Cohesion: 0.09
Nodes (21): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, start, name (+13 more)

### Community 125 - "alert-email-preview.yml"
Cohesion: 0.10
Nodes (20): TO, TOKEN, WORKER_URL, to, jobs, send, name, on (+12 more)

### Community 126 - "test_projects_scale.py"
Cohesion: 0.20
Nodes (6): bind(), row(), ScaleArtifactTests, ScalePolicyTests, ScaleReconciliationTests, current()

### Community 127 - "env"
Cohesion: 0.09
Nodes (22): ANTHROPIC_API_KEY, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, BATCH, CALLS, CONFIRM, COUNTRY_CAP (+14 more)

### Community 128 - "copy"
Cohesion: 0.43
Nodes (6): choose(), country_map(), eligible(), main(), read(), resolve()

### Community 130 - "context.py"
Cohesion: 0.24
Nodes (4): features(), _last(), session_start(), sigma_daily()

### Community 133 - "enrich_page"
Cohesion: 0.24
Nodes (7): clean_title(), enrich_page(), finalize(), meta(), paywalled(), published_time(), stamp()

### Community 134 - "ClaudeProviderTests"
Cohesion: 0.20
Nodes (3): ClaudeProviderTests, FakeClaude, boom()

### Community 135 - "markets_pilot/registry.py"
Cohesion: 0.17
Nodes (10): coverage(), digest(), finite(), fiscal_year(), ident(), provenance(), read(), entity() (+2 more)

### Community 136 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 138 - "connections.test.mjs"
Cohesion: 0.08
Nodes (20): cold, env, busy, env, NOW, quiet, stories, warmIx (+12 more)

### Community 139 - "ingest"
Cohesion: 0.25
Nodes (7): jobs, name, on, workflow_dispatch, permissions, actions, contents

### Community 140 - "backfill-photos.py"
Cohesion: 0.26
Nodes (7): main(), resize(), run(), save(), save_progress(), slug(), top_up()

### Community 141 - "methods.py"
Cohesion: 0.39
Nodes (4): IdentifierTests, match(), normal_id(), valid_isin()

### Community 142 - "Downloads"
Cohesion: 0.25
Nodes (3): Client, NoRedirect, Downloads

### Community 144 - "generate"
Cohesion: 0.29
Nodes (8): cancel-in-progress, group, concurrency, if, runs-on, timeout-minutes, concurrency, generate

### Community 145 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 146 - "steps"
Cohesion: 0.39
Nodes (8): steps, steps, id, if, name, run, uses, working-directory

### Community 149 - "exchange_hours.py"
Cohesion: 0.43
Nodes (5): active_time(), calendar_metadata(), value(), enrich(), main()

### Community 150 - "enrich_page"
Cohesion: 0.32
Nodes (3): PageFetcher, paywalled_host(), same_site()

### Community 151 - "inputs"
Cohesion: 0.29
Nodes (7): description, required, default, description, confirm, gemini_model, inputs

### Community 153 - "re"
Cohesion: 0.13
Nodes (11): _num(), validate(), clean(), display(), exchange(), main(), slugify(), parse() (+3 more)

### Community 155 - "Projects scale — stage 1, 11 November 2026"
Cohesion: 0.17
Nodes (10): Licensing evidence / asked, not used, Outputs and limits, P19 draft project data, Projects data — current scale draft, Reproduce, Licensing and blockers, Projects scale — stage 1, 11 November 2026, Reproduce (+2 more)

### Community 157 - "writer"
Cohesion: 0.40
Nodes (5): writer, default, description, options, type

### Community 158 - "sources"
Cohesion: 0.40
Nodes (5): sources, default, description, options, type

### Community 159 - "writer"
Cohesion: 0.40
Nodes (5): writer, default, description, options, type

### Community 162 - "error_message"
Cohesion: 0.29
Nodes (4): transport(), error_message(), recording(), call()

### Community 164 - "country_cap"
Cohesion: 0.50
Nodes (4): default, description, required, country_cap

### Community 165 - "parse_time"
Cohesion: 0.33
Nodes (3): parse_time(), rss(), one()

### Community 166 - "end_date"
Cohesion: 0.50
Nodes (4): default, description, required, end_date

### Community 167 - "gdelt_files"
Cohesion: 0.50
Nodes (4): default, description, required, gdelt_files

### Community 168 - "test_markets_pilot.py"
Cohesion: 0.27
Nodes (5): runner(), execute(), main(), plan(), write()

### Community 169 - "update_asset_analysis.py"
Cohesion: 0.39
Nodes (6): ai(), load(), main(), related(), template(), vol()

### Community 170 - "regions"
Cohesion: 0.50
Nodes (4): regions, default, description, required

### Community 171 - "start_date"
Cohesion: 0.50
Nodes (4): start_date, default, description, required

### Community 172 - "connections_only"
Cohesion: 0.50
Nodes (4): default, description, type, connections_only

### Community 175 - "Regional article and connection recovery"
Cohesion: 0.22
Nodes (8): Before running, Dry run first, Model, regional reserves, repairs and cost, Months-back backfill through GDELT (Aug 1 – Oct 15 2026), Offline verification, Regional article and connection recovery, Routing, persistence and capacity, Writer: Claude Haiku 5.5 (default) or Gemini

### Community 178 - "P19 Part A · draft ingestion foundation, expanded coverage blocked"
Cohesion: 0.22
Nodes (8): Asked, not used, Build-report table, Files changed, Licensing evidence, Not done, Open questions / owner decisions, P19 Part A · draft ingestion foundation, expanded coverage blocked, Tests run

### Community 179 - "US / UK Markets pilot — artifact and API code only"
Cohesion: 0.25
Nodes (7): Attribution, budget and sizing, Current result and limits, FX, Read-only API and manual publication boundary, Run and review (no publication), US / UK Markets pilot — artifact and API code only, Verification before branch push

### Community 181 - "Isolated priority-news trial"
Cohesion: 0.20
Nodes (9): Explicit publication boundary, Full-article storage trial, Isolated calendar adapter, Isolated non-AI data jobs, Isolated priority-news trial, Isolation, Offline checks, Operation after explicit deployment approval (+1 more)

### Community 182 - "Country coverage audit"
Cohesion: 0.33
Nodes (5): Before / after status, Cost and blockers, Country coverage audit, Measurement limits, Regional priorities

### Community 183 - "Projects media — stage 2 preparation"
Cohesion: 0.33
Nodes (5): Actual pass, 11 November 2026, Approve and attach individual files, Projects media — stage 2 preparation, Run candidate collection, Validation and remaining work

### Community 186 - "Deployment preparation — inactive proposal"
Cohesion: 0.33
Nodes (5): Deployment preparation — inactive proposal, DNS preservation and approval sequence, Owner accounts and settings checklist, Priority-news workflow, Worker prerequisites and exact configuration gap

### Community 189 - "One-off outage recovery — staging only"
Cohesion: 0.33
Nodes (5): Actual one-hour staging attempt, Boundary evidence (UTC), Implementation and safety, One-off outage recovery — staging only, Operator steps after review

### Community 190 - "ingest"
Cohesion: 0.40
Nodes (5): if, needs, runs-on, timeout-minutes, ingest

### Community 192 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 193 - "Live Globe connections — draft delivery fix"
Cohesion: 0.33
Nodes (5): Frontend and history boundary, Live Globe connections — draft delivery fix, Offline verification, Review / owner release sequence, Worker storage and read API

### Community 194 - "Backend news cleanup"
Cohesion: 0.40
Nodes (4): Backend news cleanup, Files changed, Results, Validation

### Community 195 - "Prediction Engine v5 candidate: FROZEN before the held-out test"
Cohesion: 0.40
Nodes (4): Held-out test (Oct 28–31): the only number that counts for this candidate, Prediction Engine v5 candidate: FROZEN before the held-out test, Rule (one change to v4, chosen on the TRAIN window only), Train window (Oct 21–27, 252 judged v4 views): what this rule was chosen on

### Community 196 - "Investedia backend"
Cohesion: 0.50
Nodes (3): Investedia backend, Owner rules (all agents: Claude, Codex, others), Who does what

### Community 197 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 198 - "Markets coverage feasibility"
Cohesion: 0.50
Nodes (3): Exchanges, Markets coverage feasibility, Recommended launch countries

### Community 199 - "Proposed identity model — no registry built"
Cohesion: 0.50
Nodes (3): Matching rules, Proposed identity model — no registry built, Provenance and visibility

### Community 200 - "manifest.json"
Cohesion: 0.50
Nodes (3): build_date, schema, sources

### Community 201 - "Projects scale — stage 3 partial source pass"
Cohesion: 0.50
Nodes (3): Projects scale — stage 3 partial source pass, Result, Source method and limits

### Community 202 - "Early calls: scoring framework v2 (frozen before scoring)"
Cohesion: 0.50
Nodes (3): Audit of the original (v1) scoring, 653 judged calls, Early calls: scoring framework v2 (frozen before scoring), Framework v2

### Community 209 - "max_usd"
Cohesion: 0.50
Nodes (4): max_usd, default, description, required

## Knowledge Gaps
- **4 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291`, `RFC-8292`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1513 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **85 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `dedupe()` connect `news_core.py` to `test_news_core.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `calendar_fred.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10256410256410256 - nodes in this community are weakly interconnected._
- **Why does `1. Audit of the current live engine (Prediction Engine v2, `impact-gemini-v2`)` connect `news_core.py` to `Prediction Engine v4: design and frozen rules`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.04985994397759104 - nodes in this community are weakly interconnected._
- **Why does `RegionalTests` connect `RegionalTests` to `error_message`, `pathlib`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `regional-backfill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10220673635307782 - nodes in this community are weakly interconnected._