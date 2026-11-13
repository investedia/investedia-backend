# Data Centres batch 1: official-directory extraction (Claude, 13 Nov 2026)

Built on Codex's `codex/data-centers-research` (merged locally, unchanged). Output follows `investedia.projects.import.v1`
and **passes Codex's importer** (602 inserted, 0 conflicts, 0 duplicates) and all five Codex test suites (OK).
Nothing published; `preview_only: true`; importer manifests stay `production_approved: false`.

## Totals
| Measure | Count |
|---|---|
| Facility pages discovered (official sitemaps/directories) | 650 (Equinix 282, Digital Realty 261, CoreSite 29, NEXTDC 25, CyrusOne 57; minus non-facility pages) |
| Parsed facility candidates | 641 |
| Matched to Codex's 61 reviewed rows (provider + official site code; **staged, not re-imported**) | 33 -> `import/staged-matches-to-codex-61.json` |
| Skipped (no country/location, or no unambiguous DLR node id) | 5 -> `import/skipped.json` |
| **New unique records imported** | **602**: Equinix 275, Digital Realty 232, CoreSite 26, NEXTDC 25, CyrusOne 44 |
| Affiliation with a verified listed issuer (EQIX Nasdaq, DLR NYSE, AMT NYSE via CoreSite, NXT ASX) | 558 |
| Fund-manager exposure, research only (CyrusOne via KKR NYSE / BlackRock NYSE; SEC Ex. 99.1 evidence) | 44 |
| Verified investment access under Codex's contract | **0** (see blocker 1) |
| Verified property ownership / legal title | **0** |
| Locations: exact / approximate / unknown | **115 / 318 / 169** |
| Stage: operating / under construction / planning | 545 / 31 / 26 |
| Countries / regions | 43 countries; Europe 212, North America 211, Asia-Pacific 106, Latin America 51, Africa 12, Middle East 5, unknown 5 |
| Imagery | 0 (professional placeholder; no photo or satellite cleared) |
| **Public-release eligible** (`public_projection` passes) | **0** |

## How locations were classified (owner rule: a pin is not automatically the building)
- **Exact (115):** operator-published pin within 150 m of the geocoded published address *and* the geocoder hit is building/address level.
- **Approximate (318):** pin within 1 km of the address (campus-level), or coordinates geocoded from the published address / locality (CoreSite, NEXTDC, CyrusOne, pages without pins). Labelled; never shown as exact.
- **Unknown (169):** pin disagrees with the address by >1 km, or the address could not be geocoded. Coordinates withheld; disposition in `notes`.
- Country: 83 records state no country on the page; derived from the operator coordinates by OSM reverse geocoding (noted per record). Codex's Dublin DUB1/DUB10 conflict is untouched (both are in the staged matches).

## Remaining blockers
1. **Investment access.** Codex's contract treats directory affiliation as *not* verified investment exposure. Each site needs per-facility operator/lease/development/ownership evidence (e.g. company press release, filing schedule) before `investment_access.verified` can be true.
2. **Source reuse.** Equinix and Digital Realty terms restrict republication; identity/status/economic fields remain `pending`. Needs owner/legal decision or a licensed source.
3. **Location reuse.** Operator pins (corporate pages) and OSM geocodes (ODbL attribution) are `pending` for release.
4. **CyrusOne.** Fund-level exposure: owner decision on whether fund-manager links may appear publicly at all.
5. **Ownership.** EQIX 10-K owned/leased and DLR Schedule III are per metro, not per facility: no per-site title.
6. Not yet covered: Iron Mountain (site rate-limited, HTTP 429), GDS, Keppel DC REIT, NTT DATA and others.

## Reproduce
```
python tools/datacentres/pipeline.py --cache <cache>
python tools/datacentres/validate_pins.py --cache <cache>
python tools/datacentres/to_import.py <cache> <registry.json> <dlr-nodes.json>
python research/data-centers/scale/import_projects.py data/datacentres/import/claude-dc-batch-1.json --output <tmp>
```
Raw pages and the registry evidence files are kept outside Git (licensing); hashes are recorded in every record.
Not investment advice.
