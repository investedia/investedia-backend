# P19 Part A · draft ingestion foundation, expanded coverage blocked

A reproducible builder now migrates retained data with explicit provenance and prevents unreviewed new sources from being ingested. **Part A's expanded verified dataset is not complete.** No production source, financial ledger, deployment or robot schedule changed. No secrets/model calls.

## Files changed

- `tools/projects/build_projects.py`, `status_map.py`, `sources/*.py`: reproducible adapters, exact statuses, licence/raw hash gates, per-field evidence, ISO/centroid validation, duplicate/conflict handling, company links and featured/photo validation.
- `tools/projects/news_links.py`, `review_news.py`, `tools/globe-news/connections.py`: exact project destinations behind a disabled 100-match human-review gate; article fields and historical paths untouched.
- `data/projects/`: retained cache + reviewed-preview YAML, pinned manifest, centroid sentinels, generated build/country-only/match reports and run guide.
- `assets/globe/projects*.json`, `project-links.json`, four retained `assets/img/projects/` photos: draft output only; not copied to the frontend.
- `.github/workflows/projects-data.yml`, PR CI dependency install, requirements, ignore rule and `tests/test_projects_pipeline.py`: manual artifact-only workflow and offline tests.

## Build-report table

| Metric | Actual draft output |
|---|---:|
| Input existing map records | 635 |
| Retained map points | 631 |
| Newly verified points | 0 |
| Countries (existing ISO map) | 78 |
| Duplicate pairs merged | 3 |
| Dropped: country not in ISO map | 1 |
| Sourced-in-retained-snapshot status | 118 / 631 (18.70%) |
| Missing status | 513 |
| Sourced status year | 0 / 631 |
| Old inception years withheld | 111 |
| Capacity / cost / owner / aliases | 0 / 0 / 0 / 0 |
| Missing year / capacity / cost / owner | 631 each |
| Listed-company links | 0 |
| Featured inherited previews | 4 |
| Newly fully reviewed featured projects | 0 |
| Real matches manually reviewed | 0; accuracy unknown; connection gate OFF |

| Type | Retained points |
|---|---:|
| Wind energy | 265 |
| Nuclear energy | 159 |
| Real estate | 183 |
| High-speed rail | 14 |
| Megaproject | 10 |
| All other 14 requested types | 0 each |

Source/status/country totals, missing fields, the three QID pairs merged, rejected country Q20569290 and all field conflicts are in `data/projects/build-report.json`. These are retained observations, not new independently verified coverage or publication approval.

## Tests run

- Offline builder hash reproducibility and 19 new fixture-based tests: pass. Every output fact has field-level provenance; unknown years/statuses/identities are not guessed. Fixtures are not production data.
- Full backend Python suite: 240 tests, pass, 4 existing skips.
- Worker tests: 76 pass.
- Java Maven verify using the prepared JDK/cache: 13 pass.
- No new failing checks. Pre-existing Python ResourceWarnings remain; default Maven home is unwritable here, so verification uses the existing workspace Maven cache and settings.
- Frontend B1/B2/B6 validation and labelled screenshots are on `codex/p19-projects-layer`; no new interface mockup is claimed approved.

## Licensing evidence

The docs audit records each proposed dataset, primary notice URL, scope and unresolved commercial redistribution review. Wikidata/GEM/World Bank probes received sandbox CONNECT403 on 11 November. No current primary notice/download was obtained. Only the exact pre-existing CC0-labelled Wikidata snapshot and four inherited preview photos are migrated, explicitly unverified; SHA-256 checks do not certify rights or correctness. New sources remain disabled and require version-specific evidence before ingestion.

## Asked, not used

OpenStreetMap/ODbL; IAEA PRIS; company/news websites; paid S&P/BNEF/Rystad/GlobalData; Google Maps. No Gemini/source substitutions. No licensed stock-price changes are claimed.

## Not done

- Current primary-source licences/commercial redistribution review, raw downloads and source-version/class/column verification are blocked. Adapters are offline-tested scaffolding, not a claim that every external spreadsheet schema was observed.
- No new 4,000-point population; 631 retained-unverified candidates remain draft. Targets are quality-dependent, never quotas.
- No 50 fully reviewed featured projects, expanded geographic/type spread or newly cleared photographs. Four inherited previews remain; not all have two milestones.
- No real verified-company links or 100-match manual accuracy table; zero verified input supports neither. Project/news connections remain off.
- Full centroid-placeholder detection across all upstream conventions needs reviewed provider metadata; the current existing-globe centroid check is limited and documented.
- Frontend visual B3–B5/B7–B8 work awaits a separate approved mockup. No production publication or live data changes.

## Open questions / owner decisions

A-Q1 resolved: ports/airports only meaningful projects, developments or expansions. A-Q2 resolved: all verified locations/basic facts free; advanced research/filtering/tracking/alerts may become Pro. A-Q3 resolved: World Bank only at precisely verifiable physical sites. No remaining product-scope question; source access and human evidence review remain blockers.

Run: `python tools/projects/build_projects.py --offline`; optional manual Actions → Projects registry (draft artifact only), default `fetch_reviewed=false`. Nothing publishes. Not investment advice.
