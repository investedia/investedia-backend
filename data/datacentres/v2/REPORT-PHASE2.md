# Data Centres Phase 2: verification, reuse and first public batch (Claude, 13 Nov 2026)

Local only. Nothing pushed, merged or deployed. Codex's adapter/importer used unchanged.
Not investment advice.

## 1. Reconciliation of all 650 discovered pages
| Step | Count |
|---|---|
| Facility pages found in official sitemaps/directories | 650 (Equinix 282, Digital Realty 261, CoreSite 29, NEXTDC 25, CyrusOne 57, minus non-facility pages) |
| Not single-facility pages / not parseable (campus or landing pages) | 9 |
| Parsed candidates | 641 |
| Matched to Codex's 61 reviewed rows (operator + official site code), **kept as Codex records**, new evidence staged | 33 |
| Duplicate source identity (same Equinix IBX listed under two metros) | 1 |
| Skipped: no location/country (2) or no unambiguous Digital Realty node id (3) | 5 |
| **Inserted in batch 1** | **602** |
| Phase 2 additions: Equinix 10-K development phases not already held by Codex | 29 (12 more rows belong to existing Codex projects and were staged, not duplicated) |
| **v2 total** | **631** (596 existing facilities + 35 development projects) |

## 2. Repeatable portfolio verification rules
A rule pairs **one documented issuer filing statement** with **the issuer's own facility page**. It proves an operating relationship, never ownership.
| Rule | Filing evidence (SEC, FY2025 10-K) | Applies to | Result |
|---|---|---|---|
| R-EQIX-OP | Item 2 portfolio of IBX data centers: 255 consolidated + 25 unconsolidated (23 xScale, MC1, SN1) | 275 Equinix facilities | Operator exposure; xScale ('x') marked unconsolidated JV |
| R-DLR-OP | "We own and operate our data centers"; JVs: "we serve as the managing member responsible for operations" | 232 Digital Realty facilities | Operator exposure; 8 records note JV platforms (MC Digital Realty 50%, Digital Connexion 33%, Bersama 50%, Mivne 50%, Medallion 60%) as business-level interests, not property stakes |
| R-AMT-OP | "30 operating data center facilities across eleven markets in the United States" | 26 CoreSite facilities (+3 in Codex rows = 29 vs 30 stated) | Operator exposure via American Tower |
| R-EQIX-DEV | Item 2 table: significant IBX projects under construction at 31 Dec 2025 (code, phase, metro, target, cabinets, capex) | 41 rows (29 new + 12 Codex) | Developer exposure with filing-stated metrics |
| none | NEXTDC annual report not obtainable in this pass | 25 | Stays directory affiliation (research only) |
| fund-level | CyrusOne 8-K Ex. 99.1 (KKR + GIP), BlackRock 8-K Ex. 99.1 (GIP acquisition) | 44 | Research only; owner decision |
Verified listed-company relationships: **562** (533 operator + 29 developer). Verified property ownership: **0**.

## 3. Commercial reuse findings
| Source | What the terms say (checked 13 Nov 2026) | Status |
|---|---|---|
| equinix.com Terms s.3 | All content "including text, **data**… photographs" is Material; may not be "copied, reproduced, distributed, republished, downloaded… posted"; use = acceptance | Contractual restriction covers data. **Escalate** |
| digitalrealty.com Terms | "Works of authorship… design, text and images"; users may not "copy, reproduce, modify, use, republish… material from the Web Site"; use = agreement | Restricts copied material; factual status unclear. **Escalate** |
| nextdc.com Terms | May not copy, reproduce… "or **commercialise any information obtained from any part of this website**" without written permission | Strictest. **Blocked without permission** |
| coresite.com | Only a privacy policy found; no website terms of use located | Lowest contractual risk; page text/images still copyrighted |
| PeeringDB (checked as an independent facility source) | Reproduction only for "Internet operational purposes"; excludes "any other commercial application" | Not usable for publication without permission |
| SEC filings (10-K tables/statements) | Public regulatory disclosures; Codex handoff: SEC facts owner-approved in scope | **Cleared** for facts with attribution, no prose copied |
| Wikidata | CC0 | **Cleared** (city references, HQ cities) |
| OpenStreetMap geocodes | ODbL: attribution, share-alike for derived databases | Internal QA only; not used in public records |

Distinctions applied: facts established from filings (publishable) vs. facts first seen on operator pages (contractual question) vs. marketing text, photos and spec tables (copyright, never copied) vs. the directory as a compilation (possible database/contract claim; we do not republish it in bulk) vs. coordinates (operator pins = page data, pending; city references = CC0, cleared).
**No legal conclusion is made that website facts are free to republish.** Escalations: (1) written permission from Equinix, Digital Realty, NEXTDC (draft request below); (2) owner/legal view on publishing minimal factual fields (code, city, operator, listed parent) independently re-expressed, given the contractual terms; (3) whether CoreSite facts can be cleared given no terms located.

## 4. Audit results
- Duplicate ids / source identities: **0** (importer-enforced; 1 Equinix cross-metro duplicate dropped in batch 1).
- Wrong development labels corrected: **51** set to "unknown" (CyrusOne 44: matched site-wide navigation; Digital Realty 6 and CoreSite RA1: generic words such as "master-planned campus"). Kept only facility-specific stages (NEXTDC 6) and SEC-table phases (29).
- Country conflicts: 2 flagged (Hong Kong vs OSM "CN" representation, no real conflict); Codex's Dublin DUB1/DUB10 conflict untouched.
- Headquarters: EQIX Redwood City, DLR Austin, AMT Boston, KKR/BLK New York (Wikidata CC0); NEXTDC Sydney (GLEIF) vs Wikidata Brisbane: conflict recorded, GLEIF used. All marked approximate city references.
- Campus vs building: 53 records share a published address with another building; kept separate (no merge on address).
- Operating vs development: 596 existing facilities (searchable, `existing_asset`, not counted as projects) vs 35 development projects.

## 5. Locations after audit (proximity alone never upgrades a point)
| Basis | Count | Precision |
|---|---|---|
| Official operator site pin, consistent (≤150 m) with the published address at building level | 115 | exact |
| Official pin 150 m–1 km from the address (campus level, unresolved) | 110 | approximate |
| Geocoded published address (no official pin) | 157 | approximate |
| Geocoded locality (suburb/city only) | 51 | approximate |
| Wikidata city reference (public candidates) | 29 | approximate |
| Withheld (pin and address disagree >1 km, or no geocode) | 169 | unknown |

## 6. Recommended first publication batch
**29 Equinix development phases from the FY2025 10-K** (`v2/public_candidates.json`): Americas 12, EMEA 9, Asia-Pacific 8; 37,250 sellable cabinets; ~US$4.8bn filing-stated capex. Every field comes from the SEC filing or Wikidata CC0. Location is a labelled city reference, no imagery (placeholder). **All 29 pass Codex's `public_projection` once the owner signs the prepared fact digest**; nothing is signed now.
Next batch candidates after reuse escalation: 533 operator-verified facilities (licensing_unresolved).

## 7. Expansion status
Iron Mountain: HTTP 429 again (not retried). GDS and Keppel DC REIT: no portfolio pages exposed at the tried URLs/sitemaps. NEXTDC annual report not found in the ASX feed window. No new operators added this pass.

## 8. Regression
Codex importer: v2 combined 631 inserted / 0 errors; public file 29 inserted / 0 errors. Codex suites (research, phase2, phase3, phase4, scale): OK. Backend `tests`: OK (4 skipped, pre-existing).

## Draft permission request (owner to send; not sent)
> Subject: Permission to reference public data-center facility facts
> Investedia is a financial news platform. We would like to show a short factual record for each of your publicly listed data-center facilities (facility code, city, country, your company as operator, your stock listing), with a link to your page and credit. We would not copy text, images, specifications or maps. Could you confirm in writing whether this use is permitted, and on what conditions?
