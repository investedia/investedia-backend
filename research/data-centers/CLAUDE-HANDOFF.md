# Data Centers research handoff to Claude

**Repository:** `investedia/investedia-backend` (private). **Collaboration branch:** `codex/data-centers-research`. This branch contains the original research history plus the later scale infrastructure. It is for collaboration, not production. No merge, deployment, shared Energy change or public dataset release is authorized by sharing it.

Start here:

- **All 61 reviewed Data Center rows:** [`phase2/phase2-dataset.json`](phase2/phase2-dataset.json). Combine `original_records` (29) + `development_records` (32); do not treat the smaller adapter examples as the full dataset.
- **Latest blockers for all 61:** [`phase4/blocker-matrix.csv`](phase4/blocker-matrix.csv), with machine-readable [`phase4/blocker-matrix.json`](phase4/blocker-matrix.json).
- **Importer / Claude 1 interface:** [`scale/CLAUDE1-INTEGRATION.md`](scale/CLAUDE1-INTEGRATION.md).
- **Source-specific reuse review:** [`phase4/REUSE-ASSESSMENT.md`](phase4/REUSE-ASSESSMENT.md).

## Recovery and history

All requested material exists; none was regenerated for this handoff. Local branches/worktrees and repository history were checked. The work was in the backend worktree `/workspace/data-centers-research`; it had not previously been pushed. Five existing commits are retained intact:

| Commit | Existing work |
|---|---|
| `0495d6b73e71cea12242394319f2e0fa1ec38df9` | Original 29-record verification batch, 26 accepted affiliations, source packets/receipts, audit and extraction/build tools |
| `d5513edb09ac68887f556f6445eb9eec9bca390f` | 61 reviewed rows, economic-role enrichment, 32 additional development/context rows, evidence packets and Real Estate source audit |
| `7be5c633a50f0722953d05b9a1e285a63391a8ef` | Per-record publication blockers, five city-reference candidate projections, isolated adapter/Globe research preview |
| `e743e2d7d34b590eed4de625de41a5c5a9682176` | Cross-sector proposal, five candidate reviews, 10-property Real Estate pilot, bounded NY3 factual review |
| `e7faaff09799a32f696ce28b919e66ad27f832a5` | Scalable ingestion, identifier-based company resolution, incremental artifacts, catalog/detail loading and capacity tests |

The research branch was advanced to the already existing descendant infrastructure commit, preserving ancestry. No main merge, rebase or history rewrite was performed. Earlier audit statements saying “local only” are historical; this handoff describes the collaboration upload. All production/reuse restrictions still apply.

## Counts: do not inflate or conflate them

| Scope | Existing result |
|---|---|
| Original batch | 29 reviewed, deduplicated records: 25 DLR + 3 Equinix + 1 CoreSite |
| Original classifications | A 26 (23 DLR + 3 Equinix), B 0, C 1, D 2 |
| Accepted original portfolio affiliations | 26, across 20 countries; **not** 26 title-verified properties or construction projects |
| Later combined Data Center research | **61 reviewed rows = 29 originals + 32 additional reviewed rows** |
| Additional rows | 26 countable development/phase rows + six non-counting campus/programme/parent contexts |
| Later original facility affiliations | 27 after CoreSite VA1's operating/parent-chain review; this is a later evidence update, not another original facility |
| Economic relationship rows | 36 including six contexts; 30 economic asset/project records after excluding those contexts |
| Issuer-reported group-owned observations | Four; overlaps other classifications, not four extra projects or legal-title verifications |
| Verified legal property titleholders | Zero |
| Exact Data Center sites / cleared photographs | Zero / zero; five priority candidates use CC0 approximate city references |
| Minimum factual Data Center review | NY3's narrow factual projection reviewed; no shared integration or production release approval |
| Real Estate | 10 property candidates: three explicit developer relationships, seven portfolio affiliations; zero verified property titles, mapped property investment routes or public-ready properties |

The 261 DLR directory entries mentioned in the original audit are a discovery count, **not 261 reviewed/verified records**. No full directory export is included.

## Verification definitions

Original A/B/C/D is a **research affiliation classification**, not a property-ownership badge:

- **A:** an official facility record supports a specific portfolio/business affiliation with the listed issuer. It does not prove titleholder, percentage, operator, current stage, revenue or direct investment rights.
- **B:** regulatory-chain route reserved/fail-closed pending a reviewed adapter; no original B records.
- **C:** incomplete company/parent evidence. Original VA1 remains C in the immutable first batch; Phase2 records its later operator/AMT chain evidence.
- **D:** contradiction/rejected for display; retain original claim and rejection reason for audit.

Later economic roles distinguish direct property ownership, subsidiary/JV property ownership, company development, lease/operation, contractual exposure, qualified issuer-reported group ownership and research-only affiliation. Do not copy the meaning of an Energy verification category onto a Data Center property claim. The adapter's `company_confirmed` evidence state is not permission for public release.

## File map and formats

| Path under `research/data-centers/` | Use |
|---|---|
| `dataset.json` | Immutable original 29 records; `records[]`, companies and scoped affiliation graph |
| `AUDIT.md`, `licensing-assessment.json` | Original source/verification/licensing decisions |
| `source-packets.json` | Bounded factual extraction packets with response receipts/hashes; not complete downloaded source pages |
| `extract_packets.py`, `build.py`, `test_research.py` | Original extraction documentation, offline builder and tests |
| `phase2/phase2-dataset.json` | Authoritative combined 61-row research/economic sidecar; original_records + development_records + companies + business_chains |
| `phase2/reviewed-developments.json` | 32 additional reviewed development/context rows, not the full 61 |
| `phase2/evidence-packets.json`, `sources-index.json`, `network.json` | Evidence packets, source indexing and scoped relationships |
| `phase2/build_phase2.py`, `PHASE2-AUDIT.md`, `INTEGRATION-HANDOFF.md` | Offline assembly, limitations and golden examples |
| `phase3/blocker-matrix.json/.csv` | Historical 61-row blocker audit; Phase4 is later |
| `phase3/city-references.json`, `headquarters-references.json` | CC0 approximate city/HQ endpoints, not surveyed facility/office points |
| `phase4/sector-records.json` | Seven example envelope records: two inherited Energy + five Data Centers, **not all 61** |
| `phase4/sector_adapter.py`, `contract.schema.json`, `CONTRACT.md` | Isolated common adapter, validation and proposed shared contract; not installed in shared code |
| `phase4/blocker-matrix.json/.csv`, `AUDIT.md` | Later all-record blockers and audit; production approval stays false |
| `phase4/field-reuse-review.json`, `dc-data-ready.json` | Exact-record bounded NY3 factual review/projection; not blanket company-source permission |
| `phase4/REUSE-ASSESSMENT.md`, `geolocation-review.json` | Source-specific reuse findings and rejected exact-site promotions |
| `phase4/real-estate-pilot.json/.csv`, `REAL-ESTATE.md` | All 10 named Real Estate candidates with evidence/individual blockers |
| `phase2/real-estate-source-audit.json` | Original five-company source audit (Prologis, SEGRO, Goodman, WDP, Montea) |
| `scale/import_projects.py`, `import.schema.json` | JSON/JSONL high-volume import, dedupe, company references, evidence/geography/image validation, incremental versioning |
| `scale/catalog.py` | Read-only catalog/filter/pagination/lazy detail/geographic-cluster reference consumer |
| `scale/prepare_real.py` | Demonstrates importing five DC + 10 RE records; **not a 61-row export** |
| `scale/make_fixtures.py`, `example.synthetic.json` | Explicit synthetic test data only; never verified research or production |
| `scale/energy_compatibility.py`, `energy-probe.mjs` | Read-only compatibility against a pinned frontend Git snapshot; no Energy writes |
| `scale/scale-results.json`, `verification-results.json` | Measured backend capacity and regression results |
| `sources/`, each phase's source receipt/index files | Original URLs, retrieval dates, response hashes and access failures; no raw corporate documents |

JSON is the evidence-rich source of truth; CSVs are review/index views, not substitutes for nested role, source, country-conflict or reuse fields. Preserve exact field names, original source dates and original ids. Raw HTML/PDF/JSON directory responses and source photographs are intentionally excluded from Git. They are not missing research to recreate blindly; re-fetch only when a future evidence review actually requires it and the source permits access.

## Available company relationships and priority examples

Issuer ids/current evidence in the saved research: Equinix `EQ:XNAS:EQIX`, Digital Realty `EQ:XNYS:DLR`, American Tower `EQ:XNYS:AMT`; Applied Digital `external:SEC:CIK0001144879:APLD` has SEC common-equity evidence but no reviewed shared-registry mapping. Listing dates/cover evidence remain in `phase2/phase2-dataset.json`; revalidate if stale rather than silently declaring present-day status.

| Id / candidate | Retained evidence and caution |
|---|---|
| `project:eqix:MD5` / `project:eqix:SV18` | Company development/opening and issuer-reported Owned schedule; legal title entity and property stake unverified. Approximate city references only; Equinix source reuse unresolved. |
| `project:eqix:SG6` | Dated 6 Nov 2026 opening overrides undated future timeline. 8 MW first phase vs 20 MW full scope. Unknown investment currency is not inferred. Operator exposure is not property title. |
| `project:coresite:DE3` | Planned operator/building development; 18 CMW building vs 60 MW campus. 170k/180k area conflict withheld; current stage/completion unconfirmed. No unproven assignment to a separate Denver JV. |
| `project:coresite:NY3` | Named operating exposure, launch/source-qualified service evidence and AMT parent chain. Narrow factual review only; no imagery/spec-table redistribution. Adjacent NY2 is a distinct facility despite shared address. |
| Original DC2 / SV1 / DX1 | Issuer Owned / Owned / Leased schedule examples. Lease is economically relevant; group-owned does not establish a deed entity or 100% facility stake. |
| Original CoreSite VA1 | Phase2 supplies operator/AMT chain evidence. Do not use generic Organization JSON-LD's Denver corporate address as a Virginia site point. |

AMT 64% / Stonepeak 36% refers to the operating **business** arrangement in the reviewed filing, not individual facility ownership. The separate Denver development JV remains distinct. Do not turn a sponsor/minority investor into a direct public property investment route.

## Rejected candidates and known false matches

- `dc:dlr:2310` DUB1 and `dc:dlr:2311` DUB10: official directory country “United Kingdom” contradicts Dublin addresses/Ireland geography. Retain the conflict and source value; do not silently map to UK or auto-clear a corrected record without review.
- Corporate Organization/HQ coordinates are not facility addresses. Company city endpoints are not exact offices/sites.
- Official and OSM points disagree for NY3 and SV18. MD5/DE3 address searches returned street-level results; no exact-site promotion.
- Same address or common announcement URL does not merge NY2/NY3, campus phases or different buildings.
- Campus/programme totals (e.g. Polaris Forge context) do not add to their child phase counts. Financing proceeds and contract revenue are not capex. Anonymous customers remain anonymous.
- Prologis/Goodman aggregate logistics disclosures do not become invented named Real Estate properties; the pilot contains no property rows for either from those aggregates.
- Montea “DC Quartz/Silica” means distribution centre in the Real Estate context, not the Data Centers sector.

## Reuse: internal collaboration versus public release

This private branch shares independently assembled factual research, original audit/code and response metadata. It does **not** share complete copyrighted company documents, commercial directory exports or unlicensed source photographs. The PNGs are historical screenshots of our own research UI/cartography, not facility photo assets. Natural Earth cartography is public domain; Wikidata structured city/HQ facts are CC0. OSM comparison points remain separately labelled ODbL/attribution, outside candidate release/Globe output.

Corporate facts, marketing prose, photos and protected compilations/access conditions are different. Source availability is not a commercial redistribution licence. Keep the original pending restrictions:

- Equinix: <https://www.equinix.com/about/legal/terms>, especially Material/data copying/republication restrictions; project reuse remains source-specific.
- Digital Realty: <https://www.digitalrealty.com/about/legal/terms>; portfolio affiliation is not a cleared commercial directory or ownership record.
- CoreSite actual checked policy: <https://www.coresite.com/privacy>. NY3's narrowly authored US factual record has a bounded assessment; this is not a blanket licence for CoreSite pages, images, specs or a bulk directory.
- SEC identifiers/facts are owner-approved in scope; issuer-authored filings/exhibits are not automatically US government works.
- Real Estate WDP/Montea/Goodman restrictions and SEGRO scoped permissions remain in `phase4/REUSE-ASSESSMENT.md` and source receipts.

No photograph is licensed/approved for Data Centers here. All public-release gates remain intact; one minimal NY3 factual review is not a released dataset. The branch can be reused as internal evidence and importer/test infrastructure without treating every row as production-eligible.

## Merge Claude's large-scale extraction without losing stronger evidence

1. Read the full 61-row dataset first, not the five-record transport example. Index existing stable ids, provider/node/facility ids, building/phase identity, source URL and country conflicts.
2. Match on provider + stable source facility/building id, or reviewed source-specific identifiers. **Never on name alone, shared address, city or shared source URL.** Preserve distinct campuses/buildings/phases.
3. Keep an existing id when a new extraction genuinely describes that same scope. Record aliases/source ids as evidence; flag uncertain matches rather than coalescing them. Do not create a second row merely because the new source uses a different title.
4. Stage new claims alongside prior evidence. Do not overwrite a stronger project-specific ownership/lease/operator document with a weaker portfolio affiliation, generic HQ object, newer but undated marketing page, or city pin. Review changed/contradictory facts field by field; preserve source date, retrieval date, scope and supersession reason.
5. Preserve rejected country/identity claims and context exclusions. New evidence may resolve them, but only with an explicit review. A generic bulk country tag does not overrule the known Dublin conflict.
6. Use the import envelope and reusable identifier-keyed company registry. Deduplication key is **sector + source_identity.authority + source_identity.id**; stable project id conflicts are rejected. Map a new extraction to an existing source identity only after the match is substantiated. The importer does not invent cross-provider identity matches.
7. Non-destructive updates retain previous immutable versions. The tool rejects changing an existing row's source identity and conflicting duplicate ids; it does not auto-merge evidence precedence. Resolve a conflict in a reviewed staging input, not by disabling a validator. Retire only with a matching prior record hash, reason and date.
8. Preserve real/synthetic separation, reuse dispositions, unknown/approximate/exact geography and per-image rights. Research-only affiliations cannot silently gain verified investment access or a public owner label.

## Offline use and tests

```sh
git fetch origin codex/data-centers-research
git switch --track origin/codex/data-centers-research
python -m unittest discover -s research/data-centers -p 'test_research.py'
python -m unittest discover -s research/data-centers/phase2 -p 'test_*.py'
python -m unittest discover -s research/data-centers/phase3 -p 'test_*.py'
python -m unittest discover -s research/data-centers/phase4 -p 'test_*.py'
python -m unittest discover -s research/data-centers/scale -p 'test_*.py'
python research/data-centers/scale/prepare_real.py
python research/data-centers/scale/import_projects.py supplied.json --output research/data-centers/scale/builds/claude-staging
```

If already on the branch, fetch/check the remote tip rather than creating another tracking branch. Tests/builds above are offline standard-library checks; the optional Energy Git-object probe also needs the pinned frontend checkout locally. Full raw source downloads are not needed to read/use the saved reviewed datasets. Generated builds are ignored and restricted to research-local output or `/tmp`.

These five research suites cover 122 tests (14 + 17 + 16 + 35 + 40). The sharing audit records the fresh run and deployment/content checks. A branch push does not run a robot, ingest news, publish KV, deploy a Worker or alter Energy production data.

Not investment advice.
