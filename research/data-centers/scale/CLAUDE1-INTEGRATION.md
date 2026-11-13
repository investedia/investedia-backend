# Interface handoff to Claude 1 — Projects scale infrastructure

This is a proposed integration boundary, **not approval to integrate shared code**. Claude 1 owns Projects design, prototypes and frontend implementation. Codex has made no frontend/layout changes in this task and has not repeated Data Center research. Everything here is isolated backend/data tooling on `codex/projects-scale-infrastructure`, based on `e743e2d`.

## 1. Supply a structured dataset

Use JSON with `schema: investedia.projects.import.v1`, explicit boolean `synthetic`, and `records`. Or use JSONL: first line `{ "header": {"schema":"investedia.projects.import.v1","synthetic":false,"companies":{...}} }`, then one record per line. Both use the same record contract. The checked-in `example.synthetic.json` is deliberately fake and can never become a real verified project by changing only its top-level flag.

The structural schema is `import.schema.json`, referencing the existing Phase4 sector-envelope proposal. The executable validator is authoritative for the additional evidence, ownership, geographic, image and cross-record rules.

### Required record fields

| Field | Required meaning |
|---|---|
| schema | `investedia.projects.sector-envelope.proposal.v2` |
| id | Stable source-derived project id. Keep current ids; never generate one from a name match. |
| source_identity | `{authority,id}` identifying the original source's project/building. Deduplication key is sector + authority + id. |
| synthetic | Exact same boolean as the batch; synthetic ids begin `test:` and classification is `synthetic`. |
| name, sector | Sector key `energy`, `data_centers`, `real_estate`; future sectors require a reviewed registry extension. Ordinary imports reject Energy, which uses its unchanged read-only adapter path. |
| asset | `category`: project/campus/building/existing_asset/programme; parent_id nullable; count_as_project boolean. Buildings need building identity evidence; programmes cannot count as projects. Campus and child buildings cannot both be additive project counts. |
| status | Canonical stage + source-qualified label + as_of date. Stages: announced/planning/under_construction/expanding/operating/completed/unknown. An elapsed target never proves completion. |
| location | Precision exact/approximate/unknown; lat/lon or null; label/basis/evidence for a known point; satellite_allowed. Unknown points do not enter clusters. |
| identity_evidence | HTTPS URL, SHA256, checked_at ISO date/time, locator. Hash scopes must distinguish source bodies from a verified input snapshot/reference file. |
| exposures | Explicit role, scope, per-project evidence, nullable property stake, listing or company_ref, HQ endpoint and investment_access. An empty list is allowed for unverified research; it is not a verified investment route. |
| imagery | Array, empty if none cleared. Never substitute a generic facility image. |
| verification | classification and supporting review metadata. Allowed states: company_confirmed, regulator_confirmed, mixed_company_and_regulator, research_only_affiliation, unverified, conflicted, synthetic. These are supplied evidence states, not automatic human fact checks. |
| reuse | Field dispositions cleared/pending/omit, basis and any exact-record review. Importing does not waive reuse restrictions or approve publication. |
| preview_only | Keep true for current research/test artifacts. All output manifests are production_approved:false. |

Optional common fields include country_code, city, notes, reported_metrics and lifecycle. Optional `extensions.data_centers` may contain IT capacity with phase/building/campus scope; `extensions.real_estate` may contain floor area, tenure and development scope. Preserve units, currency, source, period and disclosure scope; do not promote lease revenue to capex or group shares to property stakes. Extensions are transported without interpreting their economic correctness.

### Company registry: resolve once, reuse across a portfolio

Optional `companies` is keyed by a stable identity, e.g. `cik:0001053507`, a 20-character LEI, `qid:Q123`, or an existing `registry:...` identity. Each entry supplies:

```json
{
  "identity": {
    "scheme": "cik",
    "value": "0001053507",
    "evidence": {"url":"https://...", "sha256":"...64 hex...", "checked_at":"2026-11-13", "locator":"Issuer identity"}
  },
  "listing": {"name":"...", "ticker":"...", "exchange":"XNYS", "exchange_mic":"XNYS", "security_type":"common_equity", "evidence":{}},
  "headquarters": {"city":"...", "lat":0, "lon":0, "precision":"approximate", "evidence":{}}
}
```

This snippet is a format illustration, not a validated company entry: replace every placeholder with substantiated data. A project exposure can then supply `company_ref` and omit repeated listing/HQ objects. It must still supply the **project-specific role evidence**. Contradictory embedded listing/HQ data is rejected. A registry update re-resolves every referenced project atomically; current security evidence and scoped stakes still need review. There are no name-only joins.

Roles: direct_property_owner, indirect_property_owner, reported_group_owner, developer, operator, lessee, investor, contractor, affiliation. Direct/indirect property ownership needs specific property proof; indirect additionally needs a sourced property chain. Operating/lease/development exposure can qualify without a deed, but cannot acquire an ownership label. Preserve CoreSite business shares separately from property stakes.

Investment access: public_equity/listed_REIT/listed_stapled_security/verified_fund/research_only. Verified access needs current documented security identifiers. A familiar ticker or a directory affiliation is insufficient. Preserve stapled securities. Existing Energy exchange labels stay intact; unresolved MIC mappings remain null.

### Geographic accuracy and imagery

Exact: record-bound site evidence. Approximate: visibly labelled city/reference location with evidence. Unknown: null coordinates, no marker. Approximate coordinates cannot request site-specific satellite images. HQ cities also remain approximate.

An image entry requires `url` (HTTPS), source_url, project_id matching the record, type, cleared rights_status, licence and credit. Satellite additionally requires an exact verified site and satellite_allowed. Retain file hash/date/resolution/scope where available. Import validates the metadata; it does not fetch, generate, authenticate or grant licences to images. Claude 1 owns rendering and professional placeholders. Unknown/uncleared imagery stays empty, with an explicit UI state rather than generic substitute photography.

## 2. Validate and build locally

```sh
python research/data-centers/scale/import_projects.py supplied.json --output research/data-centers/scale/builds/data-centers
python research/data-centers/scale/import_projects.py update.jsonl --output research/data-centers/scale/builds/data-centers --incremental
```

Python standard library only; Linux/POSIX file locking. No cloud secrets, paid services, workflows, deployment, network fetching or production publisher is used. Outputs are restricted to this task's ignored `builds/` or `/tmp`; a frontend production directory is rejected.

Each import is all-or-nothing. Conflicting duplicates, invalid evidence/coordinates, unknown company refs or invalid hierarchy reject the batch. Identical duplicate ids are counted/skipped. Same names or shared announcement URLs do **not** merge buildings. Changed source identities are rejected. Only an explicit retirement request with the prior record digest, reason and date hides a record; the record remains auditable. A failed build retains `current.json` and previous versions. Concurrent imports are rejected while another writer holds the lock.

Errors are structured `{row,code,field}` and never echo supplied credential values. Examples: source_identity_required, source_identity_collision, conflicting_duplicate_id, identity_changed, contract_invalid, evidence_date_or_hash_invalid, unknown_company_reference, company_reference_conflict, energy_read_only, synthetic_boundary_mismatch, invalid_hierarchy_or_bundle. `contract_invalid` requires checking the documented envelope; the validator does not currently return a separate JSON Pointer for every nested semantic rule.

Limits: 64 MiB input, 100,000 rows/state, ids/source ids ≤200 characters, query text ≤160 characters, result pages ≤200. These are guards, not proof of 100,000-record performance; benchmarks cover up to 5,000. Full validation is linear in the batch plus hierarchy depth; there is no expensive per-record network integration.

## 3. Consume the artifacts after contract approval

Output root:

```text
current.json
versions/<version>/manifest.json
versions/<version>/catalog.json
versions/<version>/state.json
versions/<version>/details/<two-hex-prefix>.json
blobs/<sha256>.json
```

`version` is the SHA256 of canonical sorted state. No build clock enters identity. Reordering an equivalent input gives the same version. Raw supplied downloads are not part of validated output. `state.json` is the full research state for incremental builds; **do not download it on initial UI load**.

1. Read `current.json`, then the selected immutable manifest and compact `catalog.json`.
2. Show sector/status/company/search filters from catalog rows, preserving verification and synthetic warnings. Exclude retired rows by default.
3. Each catalog row has a `shard` prefix. `manifest.detail_refs[prefix]` gives its content hash; fetch `blobs/<hash>.json` only when a project detail is opened. Verify SHA256 against the manifest.
4. Cache detail blobs by hash. A one-record update changes one shard; unchanged detail URLs remain stable across versions. Versioned `details/` paths remain an offline/replay alternative and use hard links locally, not duplicate data copies.
5. Use the exact id to select the record within a shard. Render evidence and relationship scope from that record. Draw only the selected project's documented HQ exposure lines; do not fabricate all-to-all asset links.
6. The reference backend consumer `Catalog.query/get/clusters` defines response shapes and validates checksums. It is not a deployed API. No shared frontend fetch path has been changed.

Catalog rows contain id/name/sector/status/asset/country/city/lat/lon/precision/company/ticker/verification/synthetic/retired/shard/search and production_approved:false. No prices or daily percentage changes are supplied. Geographic grid clusters report count, a representative centroid, whether approximate points are present and up to five sample ids. A cluster centroid is **not** an exact site. Bounds support antimeridian crossing. Unknown positions remain searchable but are not mapped.

For an eventual static/provider implementation, use immutable blob URLs, ETags/content hashes and gzip/Brotli. The local gzip sizes in the benchmark are measured; CDN compression/latency is not. Approve provider/publish changes separately before hosting any real or synthetic artifact.

## 4. Synthetic isolation and testing

```sh
python research/data-centers/scale/make_fixtures.py --count 1000 --output /tmp/projects-test.json
python research/data-centers/scale/import_projects.py /tmp/projects-test.json --output research/data-centers/scale/builds/synthetic
python research/data-centers/scale/benchmark.py
python -m unittest discover -s research/data-centers/scale -p 'test_*.py'
```

Capacity fixtures use `test:` ids, synthetic names/companies/evidence/status/coordinates, and no actual imagery or investment access. Synthetic and real research roots cannot be merged. Synthetic verification cannot pass the existing public-review guard. The checked-in example is synthetic; generated volume artifacts are ignored and never staged as production data.

Real import demonstration reuses the previous five Data Center and ten Real Estate records via `prepare_real.py`. No new research or release decisions were made. Added transport metadata does not silently re-sign an earlier exact-record review. Both test and real research manifests remain production_approved:false.

## 5. Energy compatibility and handoff boundaries

The checked live source and latest frontend main at `f1ad144d8553e927d72ae333170eb01887adf223` contain **186 unique Energy projects and 187 verified company exposures**, not 187 unique projects. Git and live source are semantically identical. All identifiers, original normalized objects, raw verification, imagery metadata, status and HQ objects are preserved. See `production-comparison.json` and `energy-compatibility.json`.

To rerun for a later approved snapshot, fetch frontend main read-only, obtain its full commit hash, then run:

```sh
python research/data-centers/scale/energy_compatibility.py --commit <40-character-frontend-commit>
```

The probe reads Git objects and never edits Energy files. The raw source and unchanged normalized output remain in ignored local builds, with committed hashes/results. Missing fields and unresolved foreign exchange MICs are preserved rather than invented. No destructive migration or ordinary Energy import is available.

Remaining approvals: shared adapter hook and role/precision semantics; actual public-record reuse review; static/API hosting and cache policy; any push, deployment or production integration. Claude 1 owns desktop/mobile rendering benchmarks, UI regressions and visual implementation. Codex's measured performance covers validation, incremental artifacts, catalog reads, filtering, lazy detail reads and backend geographic clustering only.

Not investment advice.
