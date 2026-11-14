# Real Estate batch 1: listed-REIT properties from SEC 10-K filings (14 Nov 2026, Claude)

Local only. Nothing pushed, merged or deployed. Energy and Data Centers data are untouched.

## Headline numbers

| Measure | Count |
|---|---|
| Researched property candidates (new) | **163** (BXP 87, Host Hotels 76) |
| Verified listed-company relationship (10-K cover ticker = current SEC listing) | 163 |
| Company-reported consolidated holding (`reported_group_owner`) | 154 |
| Developer of a named construction/redevelopment project | 8 |
| Lessee (hotel leased from a third party, not owned) | 1 |
| **Verified legal property title** | **0** (filings do not name the title-holding entity; never inferred) |
| Company-stated ownership share of a specific property | 4 (BXP JV projects: 55%, 50%, 20%, 19.46%) |
| Hotels on land leased from a third party (ground lease) | 17 |
| Hotels not wholly owned (share not stated) | 1 |
| Location: exact / approximate (city point) / unknown | 0 / 86 / 77 |
| Usable imagery | 0 (placeholders; no exact site points yet, so satellite imagery is not allowed) |
| Pass every publication check except your record-by-record review | 163 |
| Publicly released | 0 |
| Research candidates (not counted above) | 10 BXP land parcels + Codex's 10 European pilot records (unchanged) |
| Rejected | 0 |

## Coverage

- Countries: US 158, Brazil 3 (Rio de Janeiro hotels), Canada 2 (Calgary, Toronto).
- Property types: Office 63, Life Sciences 10, Residential portfolio property 2, Hotel 77, Parking 2, Development 7, Redevelopment 2.
- Status: operating 154, under construction/redevelopment 8, unknown 1 (development cost on the books, no milestone stated).
- Top cities (BXP): Cambridge 17, Waltham 14, Reston 12, New York 8, Washington 7, Boston 5, Lexington 5, San Francisco 5.
- **Gap:** batch 1 is US-heavy. Europe, UK, Japan, Singapore, Australia, Middle East, Africa and Latin America are not yet covered; those exchanges have no free filing database with clear reuse terms like SEC EDGAR. Codex's 10 European pilot records (SEGRO, WDP, Montea) remain reuse-blocked.

## How each record is verified

- **Identity:** a named row in the 10-K (BXP Schedule III / construction table; Host Item 2 hotel table, with 72 of 76 hotels also matched by name in Host's Schedule III). Each record keeps the filing URL, SHA-256 and the exact row.
- **Listed company:** the 10-K cover securities table (common stock, ticker, exchange) must match the current SEC submissions record (also hashed). BXP: NYSE `BXP`. Host Hotels: Nasdaq `HST`.
- **Relationship:** "Held in the company's consolidated real estate" is not legal title. Joint ventures, ground leases and full leases follow the filing's footnotes; when a share is not stated it is left blank.
- **Status:** "operating" only where the building is depreciated (in service) or listed as an operating hotel. Construction dates are company targets, labelled as targets.
- **Location:** a city point from the US Census Gazetteer (public domain), labelled "city reference point, not the building". Host hotels give only a state or country, so their location is unknown and they get no map pin.
- **Investment route:** "indirect listed-REIT equity exposure only; buying shares gives no title to this property".
- **Not carried:** rents, yields, valuations, occupancy, cost columns, returns.

## Companies audited (10 SEC filers, FY2025 10-K)

| Company | Listing check | Rows found | Used in batch 1 |
|---|---|---|---|
| HOST HOTELS & RESORTS, INC. | OK HST | 76 | yes |
| SIMON PROPERTY GROUP INC. | OK SPG | not parsed (schedule layout) | next batch |
| BXP, Inc. | OK BXP | 87 | yes |
| VORNADO REALTY TRUST | OK VNO | 43 | next batch |
| AVALONBAY COMMUNITIES INC | BLOCKED: 10-K cover ticker not in current SEC submissions | 316 | no |
| VIVMARK RESIDENTIAL | BLOCKED: 10-K cover ticker not in current SEC submissions | aggregated (portfolio groups, not properties) | no |
| Park Hotels & Resorts Inc. | OK PK | 32 | next batch |
| SL GREEN REALTY CORP | OK SLG | 26 | next batch |
| FEDERAL REALTY INVESTMENT TRUST | OK FRT | not parsed (schedule layout) | next batch |
| ESSEX PROPERTY TRUST, INC. | OK ESS | 226 | next batch |

AvalonBay: the 10-K cover shows `AVB`, but current SEC records list no ticker. Equity Residential: current SEC records show **Vivmark Residential (VMRK)**. Neither listing is asserted until it is confirmed.

## Source and licensing audit

| Source | Used for | Terms | Status |
|---|---|---|---|
| SEC EDGAR 10-K (BXP, Host) | identity, status, relationship, listing | US federal filings; facts only, no tables or prose copied | cleared on the same SEC basis you approved for the 29 Equinix records (#109) |
| SEC submissions JSON | current ticker/exchange, CIK | US federal data | cleared |
| US Census 2024 Gazetteer places | city reference points | public domain | cleared |
| SEGRO / WDP / Montea / Goodman / Prologis web pages (Codex pilot) | 10 research records | corporate terms; personal/non-commercial clauses | still pending, unchanged |
| Imagery | none | - | none used; no royalty-bearing images |

## Importer and regression

- Codex importer (`scale/import_projects.py`), Real Estate alone: 163 inserted, 0 errors.
- On top of the 602-record Data Centers batch: 765 total, 163 inserted, 0 collisions. Re-running gives 163 unchanged (idempotent).
- `public_projection`: all 163 pass every check except "record-bound reuse review required", which only you can sign.
- Codex suites: sector_adapter 25, real_estate 10, ingestion 40, phase3 16, phase2 17, research 14. **All 122 tests pass.**
- The importer rejects Energy by design; Energy and frontend files are not touched.

## Your decisions

1. Release: sign the record-bound review for some or all of the 163 (SEC + Census only).
2. Map pins: should hotels with only a state or country stay unpinned, or get address-level research next (exact points then allow satellite imagery)?
3. Next batch: Vornado 43, SL Green 26, Park Hotels 32, Essex 226 (all listing-checked), or non-US sources first.

Files: `data/realestate/batch1/` (import-batch1.json, stats.json, companies-audit.json, research-candidates.json, rejected.json); builder `tools/realestate/build_batch1.py`.
