# Graph Report - investedia-calendar-trial-mq9oz80m  (2026-11-23)

## Corpus Check
- 257 files · ~161,403 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .otf 3, .toml 2)

## Summary
- 3114 nodes · 6077 edges · 184 communities (136 shown, 48 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2e8b07df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Outcome
- calendar_fred.py
- pathlib
- regional-backfill.py
- json
- update_news_track.py
- MarketsPilotTests
- SnapshotRepositoryTest.java
- ApiContractTest.java
- feed_inventory.py
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
- news.js
- worker-contracts.mjs
- with
- steps
- update_share_cards.py
- news-gap-backfill.py
- update_globe_news.py
- steps
- steps
- engine/policy.py
- urllib_parse
- NewsService.java
- markets_audit/run.py
- news_core.py
- SnapshotResponseHeaders.java
- fetch.py
- markets.js
- connections.js
- update_market.py
- FileMarketRepository.java
- regional-backfill.test.mjs
- events.py
- gdelt-backfill.py
- alerts.js
- steps
- NewsImpacts
- calendar_official.py
- NewsPhotos
- with
- .missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths
- update_asset_analysis.py
- env
- AzureEditorTests
- policy.test.mjs
- newscore.js
- with
- math
- with
- LicensingEvidenceTests
- server
- time
- inputs
- datetime
- audit.py
- news-gap-backfill.yml
- steps
- runner.py
- gen-companies.py
- regional-backfill.yml
- Policy
- StrictNewsTests
- fx_audit
- markets_pilot/registry.py
- ref_node_assert
- ApiConfiguration.java
- collections
- inputs
- with
- with
- sys
- balance
- Downloads
- BudgetExceeded
- publish.py
- PhotoPoolTests
- steps
- LiveConnectionsTests
- hashlib
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
- test_projects_pipeline.py
- dry_run
- gemini_calls
- SavedFeeds
- BasicsTests
- FeedsTests
- StageIntegrationTests
- PushNews
- build_projects.py
- test_outcome_v2.py
- sources
- com.investedia:investedia-backend
- com.investedia:investedia-services
- with
- steps
- os
- thin-recent.yml
- alert-email-preview.yml
- current
- env
- re
- RegionalTests
- test_news_core.py
- ClaudeEditor
- ProjectsPipelineTests
- update_news_prices.py
- EndToEndTests
- extract.py
- batch_size
- org.springframework.web.bind.annotation.GetMapping
- waitlist.test.mjs
- gdelt-backfill.yml
- backfill-photos.py
- main
- run
- test_gdelt_backfill.py
- generate
- with
- steps
- AuditInputTests
- PublishLibrary
- copy
- PageFetcher
- inputs
- CalendarTrialTests
- parse_time
- DiscoveryTests
- news-pipeline.py
- ingest
- writer
- sources
- writer
- fetch_sources.py
- ClaudeWriterTests
- error_message
- dry_run
- country_cap
- gemini_calls
- end_date
- gdelt_files
- max_usd
- atomic_write
- regions
- start_date
- connections_only
- ConnectionTests
- dedupe
- NewsTrialTests
- HoursTests
- news.test.mjs
- TrialExportTests
- AuditTests
- CachedRepresentationTests
- LegacyRetryBudgetTests

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
10. `env` - 18 edges

## Surprising Connections (you probably didn't know these)
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py
- `server` --calls--> `fetch()`  [EXTRACTED]
  tests/news-ingest.integration.mjs → workers/live/index.js
- `checked_fetch()` --calls--> `transport()`  [INFERRED]
  tools/coverage/source_licensing.py → tests/test_regional_backfill.py
- `regional_candidates()` --indirect_call--> `c()`  [INFERRED]
  tools/regional-backfill.py → tests/test_news_regions.py
- `reg_place()` --calls--> `norm()`  [INFERRED]
  tools/globe-news/connections.py → news_core.py

## Import Cycles
- None detected.

## Communities (184 total, 48 thin omitted)

### Community 0 - "Outcome"
Cohesion: 0.29
Nodes (3): Context, Outcome, session()

### Community 1 - "calendar_fred.py"
Cohesion: 0.09
Nodes (18): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), FredError, _get() (+10 more)

### Community 2 - "pathlib"
Cohesion: 0.07
Nodes (3): EnglishHeadlineTests, ExtraFeedsTests, ThinCapTests

### Community 3 - "regional-backfill.py"
Cohesion: 0.11
Nodes (33): content_hash(), archive(), batches(), cached_patch(), contains_secret(), dedupe(), draw_connections(), english_headlines() (+25 more)

### Community 4 - "json"
Cohesion: 0.10
Nodes (19): facts(), load(), main(), parse(), main(), publish(), robot_stories(), site_stats() (+11 more)

### Community 5 - "update_news_track.py"
Cohesion: 0.11
Nodes (16): Ledger, story(), Track, bars(), bench_of(), call_start(), freeze(), judge() (+8 more)

### Community 6 - "MarketsPilotTests"
Cohesion: 0.10
Nodes (7): MarketsPilotTests, plan(), build(), fx_relationships(), reconcile(), find(), union()

### Community 7 - "SnapshotRepositoryTest.java"
Cohesion: 0.10
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "ApiContractTest.java"
Cohesion: 0.06
Nodes (4): ApiContractTest, TimeConfiguration, LayeredArchitectureTest, LocalStartupTest

### Community 9 - "feed_inventory.py"
Cohesion: 0.27
Nodes (6): configured(), dates(), get(), main(), NoRedirect, probe()

### Community 10 - "live/index.js"
Cohesion: 0.13
Nodes (23): ALIAS, ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), withAliases() (+15 more)

### Community 11 - "prices.js"
Cohesion: 0.13
Nodes (31): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, NOW, day() (+23 more)

### Community 12 - "registry.py"
Cohesion: 0.10
Nodes (11): ascii_lower(), get(), name_key(), norm_ticker(), Registry, same_company(), stamp(), words() (+3 more)

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

### Community 21 - "news.js"
Cohesion: 0.09
Nodes (30): generate(), FEEDS, PROMPT, buildStories(), canonicalValue(), CONNECTION_FIELDS, DIRS, GAP_END (+22 more)

### Community 22 - "worker-contracts.mjs"
Cohesion: 0.08
Nodes (17): env, expected, feed, now, p, quotes, snapshots, source (+9 more)

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
Cohesion: 0.07
Nodes (29): active_sources(), collect(), checked_fetch(), contains_secret(), get(), LegalLinks, main(), cached_fetch() (+21 more)

### Community 27 - "update_globe_news.py"
Cohesion: 0.15
Nodes (19): backfill_impacts(), compact48(), describe(), err(), gdelt(), gemini(), gemini_models(), get() (+11 more)

### Community 28 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 30 - "engine/policy.py"
Cohesion: 0.15
Nodes (10): exit_bar(), judge(), move_between(), _sessions(), decide(), horizon(), meaningful(), _pct() (+2 more)

### Community 31 - "urllib_parse"
Cohesion: 0.06
Nodes (22): DiscoveryTests, MediaTests, ScaleTransportTests, commons_candidate(), discover(), main(), query(), text() (+14 more)

### Community 32 - "NewsService.java"
Cohesion: 0.17
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "markets_audit/run.py"
Cohesion: 0.18
Nodes (11): AuditScopeTests, RunnerBoundaryTests, coverage(), fetch_audit(), licensing(), main(), read(), render_coverage() (+3 more)

### Community 34 - "news_core.py"
Cohesion: 0.12
Nodes (13): age_minutes(), authority_of(), canon(), dedupe(), entities(), freshness(), from_iso(), jaccard() (+5 more)

### Community 35 - "SnapshotResponseHeaders.java"
Cohesion: 0.14
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "fetch.py"
Cohesion: 0.14
Nodes (14): ecb_xml(), collect(), companies_house(), confirmed_ogl(), gleif(), golden_urls(), walk(), local() (+6 more)

### Community 37 - "markets.js"
Cohesion: 0.23
Nodes (17): fixture, setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer() (+9 more)

### Community 38 - "connections.js"
Cohesion: 0.14
Nodes (17): now, clean(), distance(), ingestConnections(), MAX_BODY, MAX_ROWS, MAX_STORED, point() (+9 more)

### Community 39 - "update_market.py"
Cohesion: 0.21
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "regional-backfill.test.mjs"
Cohesion: 0.36
Nodes (8): article(), backfilled(), body(), impact, iso(), NOW, post(), seed()

### Community 42 - "events.py"
Cohesion: 0.08
Nodes (11): family(), load_days(), record(), _t(), threads(), upsert(), _write(), write_threads() (+3 more)

### Community 43 - "gdelt-backfill.py"
Cohesion: 0.07
Nodes (22): country_allowed(), day(), dedupe(), generate(), gkg_plan(), gkg_url(), GkgClient, headline_key() (+14 more)

### Community 44 - "alerts.js"
Cohesion: 0.11
Nodes (40): RFC-8291, RFC-8292, te, about(), alertsReady(), channelsFor(), country(), COUNTRY_ALIAS (+32 more)

### Community 45 - "steps"
Cohesion: 0.11
Nodes (18): jobs, offline-trial, name, runs-on, steps, timeout-minutes, on, pull_request (+10 more)

### Community 47 - "calendar_official.py"
Cohesion: 0.28
Nodes (8): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar

### Community 49 - "with"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, if, runs-on, steps, timeout-minutes, jobs (+22 more)

### Community 50 - ".missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths"
Cohesion: 0.16
Nodes (5): CallController, LedgerDocument, CallRepository, CallService, SnapshotRepositoryTest

### Community 51 - "update_asset_analysis.py"
Cohesion: 0.15
Nodes (10): features(), _last(), session_start(), sigma_daily(), ai(), load(), main(), related() (+2 more)

### Community 52 - "env"
Cohesion: 0.11
Nodes (18): ANTHROPIC_API_KEY, BACKFILL_BATCH_INPUT, BACKFILL_CALLS_INPUT, BACKFILL_CONFIRM_INPUT, BACKFILL_CONNECTIONS_INPUT, BACKFILL_DAYS_INPUT, BACKFILL_DRY_RUN_INPUT, BACKFILL_SOURCES_INPUT (+10 more)

### Community 54 - "policy.test.mjs"
Cohesion: 0.24
Nodes (10): NewsTrial, TrialEgress, destination(), egress(), route(), safeDiagnostic(), SOURCE_HOSTS, source (+2 more)

### Community 55 - "newscore.js"
Cohesion: 0.17
Nodes (20): NOW, V, emptyNewsStats(), fnv(), refreshNews(), authority(), canon(), contentHash() (+12 more)

### Community 56 - "with"
Cohesion: 0.05
Nodes (40): default, description, concurrency, cancel-in-progress, group, GH_TOKEN, backfill_run, jobs (+32 more)

### Community 57 - "math"
Cohesion: 0.18
Nodes (9): expected(), correlation(), dated(), ecb_rates(), exchange_connections(), fetch(), main(), NoRedirect (+1 more)

### Community 58 - "with"
Cohesion: 0.05
Nodes (37): runs-on, steps, timeout-minutes, default, description, type, concurrency, cancel-in-progress (+29 more)

### Community 60 - "server"
Cohesion: 0.17
Nodes (11): name, include-message, include-stacktrace, investedia, repository-root, server, address, error (+3 more)

### Community 61 - "time"
Cohesion: 0.22
Nodes (9): sparql(), get(), assets(), clean(), fetch(), for_asset(), google(), main() (+1 more)

### Community 62 - "inputs"
Cohesion: 0.13
Nodes (15): description, required, default, description, required, default, description, confirm (+7 more)

### Community 63 - "datetime"
Cohesion: 0.17
Nodes (5): Daily, day(), judge_daily(), load(), run()

### Community 64 - "audit.py"
Cohesion: 0.30
Nodes (11): assets_for(), date(), fetch_api(), finite(), generate(), main(), markdown(), NoRedirect (+3 more)

### Community 65 - "news-gap-backfill.yml"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "steps"
Cohesion: 0.17
Nodes (12): if, runs-on, steps, timeout-minutes, jobs, backfill, id, if (+4 more)

### Community 67 - "runner.py"
Cohesion: 0.14
Nodes (12): backfill(), store(), allowed(), decode_bundle(), encode_bundle(), GenerationFailed, Handler, pack() (+4 more)

### Community 68 - "gen-companies.py"
Cohesion: 0.31
Nodes (5): clean(), display(), exchange(), main(), slugify()

### Community 69 - "regional-backfill.yml"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, name, on, workflow_dispatch, permissions, actions (+1 more)

### Community 72 - "fx_audit"
Cohesion: 0.44
Nodes (3): FXTests, fx_audit(), pearson()

### Community 73 - "markets_pilot/registry.py"
Cohesion: 0.16
Nodes (14): IdentifierTests, match(), normal_id(), returns(), valid_isin(), coverage(), digest(), finite() (+6 more)

### Community 74 - "ref_node_assert"
Cohesion: 0.07
Nodes (19): target, feed, NOW, article(), gap(), now, req(), seed() (+11 more)

### Community 76 - "collections"
Cohesion: 0.20
Nodes (11): history(), km(), load(), main(), _rules(), reg_place(), candidates(), connections() (+3 more)

### Community 77 - "inputs"
Cohesion: 0.22
Nodes (9): default, description, required, end, review_json, staging_run_id, description, description (+1 more)

### Community 78 - "with"
Cohesion: 0.22
Nodes (9): with, github-token, if-no-files-found, name, path, persist-credentials, python-version, retention-days (+1 more)

### Community 79 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 80 - "sys"
Cohesion: 0.11
Nodes (4): get(), group(), main(), get()

### Community 81 - "balance"
Cohesion: 0.39
Nodes (3): Balance, c(), balance()

### Community 82 - "Downloads"
Cohesion: 0.25
Nodes (3): Client, NoRedirect, Downloads

### Community 83 - "BudgetExceeded"
Cohesion: 0.19
Nodes (4): BudgetExceeded, ClaudeWriter, ModelBudget, ModelUnavailable

### Community 84 - "publish.py"
Cohesion: 0.24
Nodes (5): runner(), execute(), main(), write(), main()

### Community 86 - "steps"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 88 - "hashlib"
Cohesion: 0.20
Nodes (6): HistoryConnections, ScaleArtifactTests, header_hash(), parse(), records(), slim()

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

### Community 106 - "test_projects_pipeline.py"
Cohesion: 0.13
Nodes (8): records(), tabular(), parse(), parse(), parse(), parse(), parse(), normalize()

### Community 107 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 114 - "build_projects.py"
Cohesion: 0.14
Nodes (17): build(), canonical(), covered(), digest(), distance(), featured(), finite(), licence_gate() (+9 more)

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
Cohesion: 0.07
Nodes (9): daily(), records(), freeze(), judge(), load(), save(), Extraction, Runner (+1 more)

### Community 124 - "thin-recent.yml"
Cohesion: 0.09
Nodes (21): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, start, name (+13 more)

### Community 125 - "alert-email-preview.yml"
Cohesion: 0.10
Nodes (20): TO, TOKEN, WORKER_URL, to, jobs, send, name, on (+12 more)

### Community 126 - "current"
Cohesion: 0.18
Nodes (6): bind(), row(), ScalePolicyTests, ScaleReconciliationTests, TabularScaleTests, current()

### Community 127 - "env"
Cohesion: 0.09
Nodes (22): ANTHROPIC_API_KEY, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, BATCH, CALLS, CONFIRM, COUNTRY_CAP (+14 more)

### Community 128 - "re"
Cohesion: 0.17
Nodes (9): clean_title(), enrich_page(), meta(), paywalled(), published_time(), parse(), parse(), query() (+1 more)

### Community 130 - "test_news_core.py"
Cohesion: 0.25
Nodes (4): iso(), cand(), Core, story()

### Community 132 - "ProjectsPipelineTests"
Cohesion: 0.29
Nodes (4): ProjectsPipelineTests, row(), company_links(), parse()

### Community 133 - "update_news_prices.py"
Cohesion: 0.14
Nodes (10): ok(), fetch(), main(), registry_listing(), ysym(), alias_known(), fetch(), fred() (+2 more)

### Community 134 - "EndToEndTests"
Cohesion: 0.06
Nodes (12): ClaudeProviderTests, Clock, EndToEndTests, model(), FakeClaude, get(), LibraryTests, push() (+4 more)

### Community 135 - "extract.py"
Cohesion: 0.31
Nodes (5): build_prompt(), calendar_expectations(), _num(), story_block(), validate()

### Community 136 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 138 - "waitlist.test.mjs"
Cohesion: 0.43
Nodes (4): CONSENT_V, hex(), joinWaitlist(), sha()

### Community 139 - "gdelt-backfill.yml"
Cohesion: 0.25
Nodes (7): jobs, name, on, workflow_dispatch, permissions, actions, contents

### Community 140 - "backfill-photos.py"
Cohesion: 0.26
Nodes (7): main(), resize(), run(), save(), save_progress(), slug(), top_up()

### Community 141 - "main"
Cohesion: 0.29
Nodes (5): call_of(), main(), context_of(), series(), v5()

### Community 142 - "run"
Cohesion: 0.11
Nodes (18): Budget, finalize(), ingest_artifact(), acknowledged(), ingest_library(), library_days(), local_events(), main() (+10 more)

### Community 143 - "test_gdelt_backfill.py"
Cohesion: 0.07
Nodes (11): AzureProviderAccepted, CommandLineTests, CountryCapTests, gkg_zip(), GkgClientTests, http_error(), OldGkgWithoutPageTitle, RecentIngestTests (+3 more)

### Community 144 - "generate"
Cohesion: 0.29
Nodes (8): cancel-in-progress, group, concurrency, if, runs-on, timeout-minutes, concurrency, generate

### Community 145 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 146 - "steps"
Cohesion: 0.39
Nodes (8): steps, steps, id, if, name, run, uses, working-directory

### Community 149 - "copy"
Cohesion: 0.21
Nodes (10): active_time(), calendar_metadata(), enrich(), main(), choose(), country_map(), eligible(), main() (+2 more)

### Community 150 - "PageFetcher"
Cohesion: 0.32
Nodes (3): PageFetcher, paywalled_host(), same_site()

### Community 151 - "inputs"
Cohesion: 0.29
Nodes (7): description, required, default, description, confirm, gemini_model, inputs

### Community 153 - "parse_time"
Cohesion: 0.33
Nodes (3): parse_time(), rss(), one()

### Community 155 - "news-pipeline.py"
Cohesion: 0.53
Nodes (4): exclusive_run(), main(), preflight(), verify_generation()

### Community 156 - "ingest"
Cohesion: 0.40
Nodes (5): if, needs, runs-on, timeout-minutes, ingest

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

### Community 163 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 164 - "country_cap"
Cohesion: 0.50
Nodes (4): default, description, required, country_cap

### Community 165 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 166 - "end_date"
Cohesion: 0.50
Nodes (4): default, description, required, end_date

### Community 167 - "gdelt_files"
Cohesion: 0.50
Nodes (4): default, description, required, gdelt_files

### Community 168 - "max_usd"
Cohesion: 0.50
Nodes (4): max_usd, default, description, required

### Community 170 - "regions"
Cohesion: 0.50
Nodes (4): regions, default, description, required

### Community 171 - "start_date"
Cohesion: 0.50
Nodes (4): start_date, default, description, required

### Community 172 - "connections_only"
Cohesion: 0.50
Nodes (4): default, description, type, connections_only

### Community 181 - "news.test.mjs"
Cohesion: 0.09
Nodes (22): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), cold, env, busy (+14 more)

## Knowledge Gaps
- **4 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291`, `RFC-8292`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1292 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GkgClient` connect `gdelt-backfill.py` to `run`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291` to the rest of the system?**
  _4 weakly-connected nodes found - possible missing edges._
- **Should `calendar_fred.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._
- **Why does `NewsPhotos` connect `NewsPhotos` to `pathlib`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.07071887784921099 - nodes in this community are weakly interconnected._
- **Why does `RegionalTests` connect `RegionalTests` to `error_message`, `pathlib`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `regional-backfill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10685249709639953 - nodes in this community are weakly interconnected._