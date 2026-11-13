# Data Centers Phase 2 — integration handoff

Local research branch only. **Do not publish or drop this data into Energy assets.** No production/shared-code changes are included. Not investment advice.

## Concrete entry points

- `phase2-dataset.json`: original29 dispositions, additional32 reviewed rows, company identity/route evidence, scope-qualified claims, four distinct count families and empty `integration.safe_public_records`.
- `network.json`: evidence-bound economic role edges; business-chain edges are separate, not automatically flattened to property stakes.
- `reviewed-developments.json`: manually read, source-qualified development/phase/programme input. Explicit `count_as_project=false` on six parent/programme rows.
- `evidence-packets.json` and `sources-index.json`: minimal factual evidence, checksum/date/URL/locator; full corporate HTML/PDFs are ignored locally.
- `geolocation-imagery-audit.json`: geographic source outcomes, licence conditions, no cleared imagery.
- `real-estate-source-audit.json`: five companies, read-only source assessment; not ingestion input.
- `preview/`: separate local Projects research interface, no live route or renderer edits.

## What can enter now

**Public Projects/Globe: nothing.** The exact list is `integration.safe_public_records=[]`.

**Internal review queue:** 30 scope-qualified asset/project economic records, plus six clearly separate parent/JV background records. Within the original sample only DC2/SV1/DX1/VA1 have a specific economic role; the other23 original DLR affiliations must remain affiliation-only. The two original Dublin source-country contradictions remain rejected, not silently corrected.

This is safe for internal source review with the explicit qualifiers. It is not authority to copy corporate material into a commercial public product. A release requires source-specific rights review/permission or a reviewed lawful basis for the precise factual reuse, identity mapping, exact-site validation where mapped, and an agreed adapter. No code silently converts a licence label or public URL into permission.

## Field mapping — proposal for a later approved adapter, not a shared schema edit

| Research field | Future use | Gate / prohibited shortcut |
|---|---|---|
| `id`, official facility/phase code | Stable source identity | Preserve provider namespace; never match name alone |
| `project_type` | Existing asset / new development / expansion | Do not turn a financial Expansion category into construction proof |
| `scope`, `parent_id`, `count_as_project` | Campus/building/phase hierarchy | Exclude parent/programme rows from project/capacity totals |
| `company` + `investment_route` | Verified listed issuer route | Existing registry IDs only for EQIX/DLR/AMT; APLD external SEC ID remains visibly unmapped |
| `economic_relationships.role` | Owner, developer, operator, lessee, investor or contractor | Investor/lessee are distinct; do not force them into legacy `own` as owners |
| `qualified_label`, `maturity`, source period | Disclosure scope and announced-vs-existing role | Planned intent is not a funded commitment or direct public project offering |
| `legal_property_owner` | Actual legal titleholder | All currently null; group-owned issuer classification does not supply the deed entity |
| `jv` / `business_chains` | Parent/control and named JV context | Never copy business64/36 or JV20/80 to arbitrary properties |
| `capacity`, `leased_capacity`, `campus_metric` | Scoped IT/power values and units | Customer-leasedMW is not property tenure; campusMW is not buildingMW |
| `cost`, `financing`, `contracted_revenue` | Separate monetary concepts | No using debt proceeds/revenue as capex; do not infer unknown currency |
| `expected_completion`, `status`, source conflict/warning | Precise, date-qualified project stage | No completion from elapsed target; preserve timing-under-assessment and conflicting source claims |
| `coordinates`, quality | Globe location | No new exact points; company pins are held. No city-centroid, nearby-building or HQ substitutions |
| `source_evidence`, claim hashes/locators | Traceable fact-by-fact audit | Retrieval date cannot replace publication/fact date |
| `public_eligible` | Release decision | All false; no automatic source/rights approval |

The current shared Energy compact dataset and existing Projects v2 do not have an agreed universal economic-exposure contract. The independent sidecar models these facts without changing either. If Claude adopts it, agree the role, scope, route and licence fields explicitly first. No verified fund route was established; no Stonepeak/private fund is being offered to visitors.

## Useful golden examples for adapter tests

1. **DX1:** lessee, economically relevant, not property owner. Must not be discarded solely for leasing.
2. **DC2/SV1:** issuer Owned classification with no100% stake or legal title entity inferred.
3. **VA1:** operator CoreSite, indirect AMT common-equity route; AMT64%/Stonepeak36% only at operating-business level.
4. **DE3:** planned18CMW building vs60CMW campus;170k/180k area conflict held; no assumed Stonepeak Denver-JV membership.
5. **SG6:** dated6 Nov2026 opening source overrides undated2027 timeline target;8MW phase vs20MW full site.
6. **Polaris Forge1:** parent400MW overview excluded from phase count;75+75MW phases not added again to campus total.
7. **APLD Building3:** $1.59bn financing also repays debt; not project cost; shared registry mapping absent.
8. **Delta Forge2:** contracted revenue distinct from capex; anonymous customer remains anonymous.
9. **Osaka5x-1:** expected Q1 2027 timing under assessment, no firm completion.
10. **NY2/NY3:** same stated address does not prove a duplicate building.

## Remaining significant decisions / access blockers

- Documented rights or reviewed legal basis for the particular corporate fact/database reuse and any imagery before public release. The owner cannot waive third-party rights by simply approving a push.
- Property-level records/contract schedules needed for23 original DLR affiliations; no role inferred from aggregate regional tables. No paid land-title access was used.
- OSM endpoint failures and no positive exact-source matches in the bounded Wikidata/Commons queries. Supply authoritative planning/site documents or complete a later successful geographic review before generating scenes.
- APLD common stock is independently checked, but a reviewed shared-registry mapping remains necessary; no registry edit is included.
- Shared role/route adapter design must be coordinated with Claude. Do not alter Energy verification, satellite/line renderer or production datasets as part of this research branch.

The read-only real-estate audit is a separate preparation artifact. Goodman partnership/stapled-security handling and property-specific legal ownership must be reviewed before any identity or record integration.
