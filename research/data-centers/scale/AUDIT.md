# Projects scale infrastructure — backend handoff

13 November 2026. Branch `codex/projects-scale-infrastructure`, based on `codex/data-centers-research` commit `e743e2d`. The owner transferred all Projects design, visual prototypes and frontend implementation to Claude 1 during this task. Codex continued only backend/data work; no UI/layout/page or shared adapter integration was created or modified.

## Delivered

- Read-only compatibility against the latest production Energy source available during this run.
- Reusable JSON/JSONL imports for Data Centers and Real Estate using the existing cross-sector envelope; no repeated facility research.
- Stable source-identity deduplication, conflicting-duplicate rejection and company registry resolution by evidenced CIK/LEI/QID/registry identifiers, never names.
- Per-record role, evidence, stage, geography, image-rights and cross-record hierarchy checks.
- Deterministic versioned local artifacts, atomic last-good selection, incremental updates, audited retirements and concurrent-writer protection.
- Compact filter/search catalog, hash-addressed lazy detail shards, integrity checks and backend geographic clustering.
- Synthetic capacity generators and measured 200/500/1,000/5,000-record tests. No generated volume fixture is committed as production data.
- [Claude 1 interface contract and instructions](CLAUDE1-INTEGRATION.md), structural schema and explicit synthetic example.

## Energy: count discrepancy resolved from sources

Latest frontend main `f1ad144d8553e927d72ae333170eb01887adf223` and the live `https://investedia.com/assets/globe/projects-invest.json` are semantically identical. Both contain **186 unique projects with 187 verified company exposure relationships**. The request's “187 projects” does not match the unique-record count in either available source; no additional project was invented.

All 186 ids, unchanged original normalized objects, complete source records, 187 verification/exposure objects, imagery metadata, HQ endpoints and status data are preserved. Read-only wrapper validation passes for all 186. Foreign exchange labels/unresolved MICs are retained rather than guessed. No Energy source file, verification policy, imagery file, pipeline or current identifier was overwritten. Full source bytes/hashes and pin are recorded in `production-comparison.json` / `energy-compatibility.json`; ignored local build output retains the full source/envelope for reproduction.

This validates the sidecar boundary, not automatic compatibility of an unmodified production loader with new sectors. The shared hook remains subject to owner approval.

## Data Center and Real Estate import capability

The real import demonstration successfully accepts the existing **five Data Center and ten Real Estate research records**. These remain research records with their previous evidence/reuse qualifications. No new source collection, record approval or legal conclusion was performed. Adding transport metadata does not automatically re-sign an earlier exact-record review.

The same importer handles thousands of supplier records with a reusable company dictionary. A company registry change re-resolves its referenced projects; project-specific economic evidence is still required. Operational/developer/lease exposure never becomes property ownership. Unknown locations stay searchable without coordinates; exact/approximate rules and satellite-image gates are enforced. Campuses/buildings/programmes do not collapse by name/address/shared URL or inflate additive counts.

Each supplied record receives deterministic validation; this checks structure, identifiers, provenance and consistency. It does not independently prove the truth of a document or grant reuse rights. Public-record curation still requires the established source/review gates. All artifacts here explicitly remain `production_approved:false`; there is no cloud publishing command.

## Measured backend performance

Measurements are on this cloud machine with Python standard-library code. Validation/artifact-build timings include tracemalloc overhead and integrity checks; query/cluster timings are warm local calls. They are not browser rendering, network/CDN or desktop/mobile interaction measurements.

| Synthetic records | Gzipped catalog | Query p95 | Clustering p95 | Validate | Build artifact |
|---:|---:|---:|---:|---:|---:|
| 200 | 5,501 bytes | 0.437 ms | 0.174 ms | 220 ms | 210 ms |
| 500 | 12,222 bytes | 0.478 ms | 0.445 ms | 571 ms | 435 ms |
| 1,000 | 23,506 bytes | 0.657 ms | 0.790 ms | 1,124 ms | 728 ms |
| 5,000 | 113,879 bytes | 0.940 ms | 3.681 ms | 6,440 ms | 2,667 ms |

At 5,000, one selected detail shard is approximately 61 KB; full state is not needed for an initial catalog load. Every tested one-record update changes **one** detail shard. Stable `blobs/<sha256>.json` URLs let the eventual consumer reuse unchanged shards across versions. Versions retain replay detail paths with hard links locally. Full results, memory measurements and exact byte counts: `scale-results.json`.

The capacity guard is 100,000 records / 64 MiB input; **only up to 5,000 was benchmarked**, not 100,000. Source material and test volumes vary in payload size. No automatic garbage collection/retention policy is activated; previous local versions are retained for audit and rollback. Shared provider, compression and retention choices require integration approval.

## Regression and integrity results

- New ingestion/loading tests: **40 passed**. Covers JSONL, incremental/no-op updates, source-id conflicts, name-only company rejection, company refresh, immutable/cached data, last-good retention, locking, checksum corruption, retirement audit, synthetic boundaries, hierarchy, locations, image rights and credential-safe errors.
- Existing backend Python: **316 tests OK, four pre-existing skips**; inherited track-backfill ResourceWarnings unchanged.
- Worker: **88 passed**.
- Java/Maven verify: **13 passed**, zero failures/errors/skips.
- Previous research phases: **82 tests passed** (14 + 17 + 16 + 35).
- All five protected baseline file hashes unchanged. No unresolved test failures.

A temporary variable-shadowing error while adding content-addressed detail storage was caught by the new tests and corrected before the final successful runs. No pre-existing failure was concealed or reclassified.

No desktop/mobile screenshots or new visual regressions were produced following the owner's reassignment to Claude 1. Browser/rendering validation belongs to his frontend integration task. Backend outputs support his sector/status/company/search controls, selected-company HQ lines and precise imagery states without prescribing a visual layout.

## Reproduce

```sh
python research/data-centers/scale/energy_compatibility.py
python research/data-centers/scale/prepare_real.py
python research/data-centers/scale/import_projects.py research/data-centers/scale/builds/real-import.json --output research/data-centers/scale/builds/real
python research/data-centers/scale/benchmark.py
python -m unittest discover -s research/data-centers/scale -p 'test_*.py'
```

See the interface handoff for JSONL, reusable company dictionaries, incremental/retirement format, artifact loading and limits. No secrets, network scraping, financial jobs, paid services or cloud writes are part of ingestion/tests.

## Remaining integration boundaries

1. Owner approves the documented shared adapter hook and role/precision semantics before shared changes.
2. Claude supplies substantiated sector datasets; unresolved reuse, imagery or verification must remain explicit. Existing research is not a mass-release approval.
3. Claude 1 implements and tests desktop/mobile consumption and rendering, using catalog-first loading and selected-project detail shards.
4. Actual publication/provider/cache/retention changes and any push/merge/deployment require separate owner authorization.

Changed files are entirely under `research/data-centers/scale/`: adapters/probes, importer, catalog consumer, fixture/preparation tools, benchmark/tests, schemas/example, results and interface/audit documents. Earlier phases, production datasets and frontend pages remain unchanged.

Not investment advice.
