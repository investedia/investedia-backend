# Projects multi-sector contract — proposed for approval

This is a locally implemented proposal. It does not authorize shared loader, Energy, Globe or production changes. `sector_adapter.py` is the executable validator and adapter; `contract.schema.json` describes its structural envelope. Phase 3 is retained unchanged.

## Boundary and backward compatibility

The Energy loader is read-only and pinned to frontend commit `c78ab084349b43e4c166fa0f6a0dde6dbae8af5c`. Its 150 verified records normalize identically on repeated runs, without input mutation. All 150 pass the new wrapper and retain the original normalized object under `legacy_energy`, unchanged. This envelope adds a sidecar rather than relabelling or rewriting the legacy result. `run_compatibility.py` reproduces the probe. The two Energy records in the preview are real existing verified records, not synthetic new projects. Existing Energy imagery is not loaded or regenerated.

The contract registers Energy, Data Centers and Real Estate. Future infrastructure sectors require an explicit registry entry; arbitrary strings are rejected. Sector-specific metrics remain separate from the common envelope. This is backward-compatible through the wrapper boundary; it is **not** a claim the current production loader can ingest new sectors unchanged.

## Common fields

| Field | Contract |
|---|---|
| Identity | Stable id, name, country, dated source URL/hash/locator. No name-only company match. |
| Asset | project, campus, building, existing_asset or programme; parent id and count flag. Programmes are not individual projects. Building identity requires scoped evidence. No campus/building count inflation. |
| Stage | announced, planning, under_construction, expanding, operating, completed or unknown; original source-qualified label and as-of date. A past target does not imply completion. |
| Economic relationship | direct_property_owner, indirect_property_owner, reported_group_owner, developer, operator, lessee, investor, contractor or affiliation. Per-property proof is required only for an actual ownership claim. |
| Parent/security | Listed name, ticker, exchange label and MIC when mapped, security type, current evidence. Existing foreign Energy exchange labels are preserved with a null unresolved MIC; no guessed venue mapping. Preserve stapled securities, preferred/common distinctions and indirect company access. |
| Verification | Company-confirmed, regulator-confirmed or research affiliation; never equate portfolio inclusion with property ownership. |
| Location | exact / approximate / unknown. Exact requires record-bound site evidence; unknown has null coordinates and no marker. Approximate requires a visible label and provenance. |
| Images | Project identity, file/source, licence, rights decision and credit. Site satellite imagery additionally requires verified exact coordinates. No generic substitutes. |
| HQ connection | Separately sourced HQ endpoint and precision; a city is never relabelled an exact office. Line means company exposure, not a property stake or investment route. |
| Investment access | public_equity, listed_REIT, listed_stapled_security, verified_fund or research_only. Verified access requires documented current security, not merely a familiar ticker. |
| Reuse | Field decisions cleared / pending / omit, their basis, reviewer/date and digest of exact selected facts. A changed record invalidates its review. |

Company/business shares do not populate property stakes. Indirect property ownership requires a record-bound, sourced property chain. Reported group-owned assets retain that qualification. Operational or developer exposure can qualify without a deed, but is never presented as direct property ownership.

## Approval requested before any shared integration

Approve or revise this concrete contract and the narrow loader hook: route approved sector releases to their adapters; preserve the original Energy path; render economic roles under **Listed-company exposure** rather than unconditional **Listed owner**; preserve geographic/HQ precision and image gates; keep research affiliations and pending-reuse fields out of public output.

The shared owner must review label semantics and the contract boundary before implementation in shared files. No such files were changed here. Data review, contract approval and production authorization are three separate states. The owner has not authorized the latter two.
