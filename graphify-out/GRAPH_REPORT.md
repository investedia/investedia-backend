# Graph Report - backend  (2026-11-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2005 nodes · 4035 edges · 121 communities (88 shown, 33 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 86 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c8326e89`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 118
- Community 119

## God Nodes (most connected - your core abstractions)
1. `run()` - 34 edges
2. `MarketsPilotTests` - 31 edges
3. `build()` - 22 edges
4. `fetch()` - 21 edges
5. `reconcile()` - 20 edges
6. `main()` - 19 edges
7. `FakeFred` - 16 edges
8. `ApiContractTest` - 16 edges
9. `JsonSnapshotReader` - 15 edges
10. `Downloads` - 14 edges

## Surprising Connections (you probably didn't know these)
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py
- `server` --calls--> `fetch()`  [EXTRACTED]
  tests/news-ingest.integration.mjs → workers/live/index.js
- `regional_candidates()` --indirect_call--> `c()`  [INFERRED]
  tools/regional-backfill.py → tests/test_news_regions.py
- `OfficialListingTests` --uses--> `Registry`  [INFERRED]
  tests/test_official_listings.py → registry.py
- `main()` --calls--> `gemini()`  [EXTRACTED]
  engine/live_v5.py → update_globe_news.py

## Import Cycles
- None detected.

## Communities (121 total, 33 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (10): build_prompt(), calendar_expectations(), story_block(), freeze(), judge(), load(), save(), Extraction (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (18): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), FredError, _get() (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (4): AuditTests, HistoryConnections, CachedRepresentationTests, LegacyRetryBudgetTests

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (36): records(), content_hash(), digest(), batches(), cached_patch(), contains_secret(), dedupe(), draw_connections() (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (14): daily(), ok(), get(), main(), main(), payload(), push(), main() (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (16): Ledger, story(), Track, bars(), bench_of(), call_start(), freeze(), judge() (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (14): MarketsPilotTests, plan(), build(), coverage(), fx_relationships(), ident(), provenance(), read() (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (3): ApiContractTest, TimeConfiguration, LocalStartupTest

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (12): RegionalTests, transport(), active_sources(), collect(), checked_fetch(), contains_secret(), get(), LegalLinks (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (29): ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), ingestCalendar(), readCalendar() (+21 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (31): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, NOW, day() (+23 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (13): call_of(), main(), context_of(), series(), v5(), ascii_lower(), get(), norm_ticker() (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (34): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, DOWNLOAD_MB, max_download_mb (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (33): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, GEMINI_API_KEY (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (33): concurrency, cancel-in-progress, group, GEMINI_API_KEY, NEWS_INGEST_TOKEN, PIXABAY_KEY, WORKER_URL, jobs (+25 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (31): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, SAMPLE_LIMIT, sample_limit (+23 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (5): MarketController, SystemController, MarketRepository, MarketService, SnapshotMetadata

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (30): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, CALENDAR_UNLICENSED (+22 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (29): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, java (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (28): concurrency, cancel-in-progress, group, default, description, runs-on, steps, timeout-minutes (+20 more)

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (25): generate(), FEEDS, PROMPT, buildStories(), CONNECTION_FIELDS, DIRS, emptyNewsStats(), fnv() (+17 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (18): target, env, expected, feed, now, p, quotes, snapshots (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, deploy (+19 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, notices, name (+19 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (16): ShareCards, ago_text(), caption(), draw_logo(), load(), move_since(), page(), parse() (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (19): articles(), ArticleText, confirm(), dedupe(), digest(), get(), in_window(), keys() (+11 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (18): backfill_impacts(), compact48(), describe(), err(), gdelt(), gemini(), gemini_models(), get() (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 30 - "Community 30"
Cohesion: 0.10
Nodes (14): cold, env, busy, env, NOW, quiet, stories, warmIx (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (13): name_key(), active_time(), calendar_metadata(), enrich(), main(), choose(), country_map(), eligible() (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "Community 33"
Cohesion: 0.13
Nodes (11): age_minutes(), authority_of(), entities(), freshness(), from_iso(), jaccard(), norm(), same_event() (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (10): feed, article(), gap(), now, req(), seed(), CONSENT_V, hex() (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (11): AuditScopeTests, RunnerBoundaryTests, coverage(), fetch_audit(), licensing(), main(), read(), render_coverage() (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.23
Nodes (17): fixture, setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer() (+9 more)

### Community 38 - "Community 38"
Cohesion: 0.19
Nodes (18): NOW, V, refreshNews(), authority(), canon(), contentHash(), dedupe(), EC (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (16): article(), backfilled(), body(), impact, iso(), NOW, post(), seed() (+8 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (9): family(), load_days(), record(), _t(), threads(), upsert(), _write(), write_threads() (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.24
Nodes (12): ecb_xml(), collect(), companies_house(), confirmed_ogl(), gleif(), golden_urls(), walk(), local() (+4 more)

### Community 45 - "Community 45"
Cohesion: 0.28
Nodes (8): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (6): atomic_write(), iso(), retain(), cand(), Core, story()

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (10): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), rssXml(), feedFetch(), geminiRows() (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.23
Nodes (4): CallController, LedgerDocument, CallRepository, CallService

### Community 51 - "Community 51"
Cohesion: 0.19
Nodes (5): features(), _last(), session_start(), sigma_daily(), expected()

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (14): BACKFILL_BATCH_INPUT, BACKFILL_CALLS_INPUT, BACKFILL_CONFIRM_INPUT, BACKFILL_CONNECTIONS_INPUT, BACKFILL_DAYS_INPUT, BACKFILL_DRY_RUN_INPUT, GEMINI_API_KEY, GEMINI_MODEL (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.25
Nodes (8): correlation(), dated(), ecb_rates(), exchange_connections(), fetch(), main(), NoRedirect, valid()

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (8): normalize_sector(), assets(), clean(), fetch(), for_asset(), google(), main(), parse()

### Community 55 - "Community 55"
Cohesion: 0.27
Nodes (10): HoursTests, assets_for(), date(), finite(), generate(), main(), markdown(), positive() (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.27
Nodes (3): Client, NoRedirect, Downloads

### Community 58 - "Community 58"
Cohesion: 0.26
Nodes (5): runner(), execute(), main(), write(), main()

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (11): name, include-message, include-stacktrace, investedia, repository-root, server, address, error (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.24
Nodes (6): configured(), dates(), get(), main(), NoRedirect, probe()

### Community 62 - "Community 62"
Cohesion: 0.17
Nodes (12): description, required, default, description, type, default, description, confirm (+4 more)

### Community 63 - "Community 63"
Cohesion: 0.23
Nodes (5): Daily, day(), judge_daily(), load(), run()

### Community 64 - "Community 64"
Cohesion: 0.25
Nodes (6): decide(), horizon(), meaningful(), _pct(), strong_catalyst(), surprise_sign()

### Community 65 - "Community 65"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (11): if, runs-on, steps, timeout-minutes, backfill, id, if, name (+3 more)

### Community 67 - "Community 67"
Cohesion: 0.29
Nodes (6): backfill(), store(), exclusive_run(), main(), preflight(), verify_generation()

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (8): apply_indicator(), get(), main(), NoRedirect, numeric(), observation(), read(), saved()

### Community 69 - "Community 69"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, jobs, name, on, permissions, actions (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.44
Nodes (3): FXTests, fx_audit(), pearson()

### Community 73 - "Community 73"
Cohesion: 0.33
Nodes (5): IdentifierTests, match(), normal_id(), returns(), valid_isin()

### Community 74 - "Community 74"
Cohesion: 0.31
Nodes (5): clean(), display(), exchange(), main(), slugify()

### Community 76 - "Community 76"
Cohesion: 0.50
Nodes (5): history(), km(), load(), main(), _rules()

### Community 77 - "Community 77"
Cohesion: 0.22
Nodes (9): default, description, required, end, review_json, staging_run_id, description, description (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.22
Nodes (9): with, github-token, if-no-files-found, name, path, persist-credentials, python-version, retention-days (+1 more)

### Community 79 - "Community 79"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.39
Nodes (6): ai(), load(), main(), related(), template(), vol()

### Community 81 - "Community 81"
Cohesion: 0.39
Nodes (3): Balance, c(), balance()

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (5): alias_known(), fetch(), fred(), main(), wanted_assets()

### Community 83 - "Community 83"
Cohesion: 0.29
Nodes (3): BudgetExceeded, ModelBudget, ModelUnavailable

### Community 84 - "Community 84"
Cohesion: 0.36
Nodes (4): fetch(), main(), registry_listing(), ysym()

### Community 85 - "Community 85"
Cohesion: 0.36
Nodes (4): exit_bar(), judge(), move_between(), _sessions()

### Community 86 - "Community 86"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 88 - "Community 88"
Cohesion: 0.29
Nodes (3): Context, Outcome, session()

### Community 90 - "Community 90"
Cohesion: 0.25
Nodes (7): name, private, scripts, bench, bench:news, test, type

### Community 91 - "Community 91"
Cohesion: 0.29
Nodes (3): canon(), dedupe(), dedupe()

### Community 97 - "Community 97"
Cohesion: 0.33
Nodes (6): GAP_END, GAP_START, NEWS_INGEST_TOKEN, REVIEW_JSON, WORKER_URL, env

### Community 103 - "Community 103"
Cohesion: 0.50
Nodes (4): default, description, type, confirm

### Community 104 - "Community 104"
Cohesion: 0.50
Nodes (4): start, default, description, required

### Community 105 - "Community 105"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 106 - "Community 106"
Cohesion: 0.50
Nodes (4): default, description, required, days

### Community 107 - "Community 107"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "Community 108"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

## Knowledge Gaps
- **2 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 778 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RegionalTests` connect `Community 9` to `Community 2`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services` to the rest of the system?**
  _2 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05974025974025974 - nodes in this community are weakly interconnected._
- **Why does `LicensingEvidenceTests` connect `Community 59` to `Community 2`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08048103607770583 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.09343200740055504 - nodes in this community are weakly interconnected._