# Real Estate Phase 5B - continuation (14 Nov 2026, Claude) - local only

Nothing pushed, merged, deployed or published. Monitoring not activated.

## 1. First release: 20 owner-selected candidates
- See `APPROVAL-MANIFEST.md` and `approval-manifest.json`. Each record carries:
  - identity and aliases;
  - company and listing evidence;
  - the relationship with its scope and stated share;
  - what qualifies it (a verified photo, or a plan with evidence);
  - the coordinate class;
  - per-field licensing;
  - attribution lines;
  - its fact_sha256;
  - `owner_approval: null`.
- 13 qualify by photo and 7 by development plan.
- Coordinates: 7 building points, 12 verified address points, 1 approximate city point (Reston Next Retail).
- 725 12th Street now has an address point. Its NW quadrant comes from BXP's property page.
- Newly eligible but kept out of the 20 (they are next candidates): 250 West 55th Street (photo now verified), plus the UK/EU and Japanese records below.

## 2. Location classes (rule 6: address geocodes are not "exact")
- US batch, current records: building point 10, verified address point 87, approximate city point 57, unknown 6.
- Only Wikidata building points (within 150 m of the company's own pin) are labelled exact. Census and GSI geocodes are "verified address point" and show no satellite imagery.
- Japan (JRE): 44 verified address points (block and lot matched) and 29 approximate district points.
- UK/EU pilot: 3 building points, 23 city points, 2 district points, 2 unknown.

## 3. Imagery
- US:
  - 14 accepted: 250 W 55th St was added after a visual check.
  - 2 rejected: interior shots.
  - 5 pending. Commons rate-limited every retry; the backoff reached 5 minutes, then 10-minute pauses, and the job was stopped rather than continuing to hit their servers.
- Japan:
  - 10 Wikidata photo matches by name and distance; 1 rejected (a neighbourhood road photo).
  - 2 licence-checked and visually accepted: Nagoya Hirokoji Building (CC BY-SA 4.0) and Tokyo Opera City (CC BY-SA 3.0).
  - 8 pending (Commons rate limit).
  - The other 63 JRE properties have no Wikidata photo match; all 73 stay in the research dataset.

## 4. UK/European pilot (`data/realestate/intl/import-eu-pilot.json`): 30 records, all with documented plans
- British Land (FY26 results), 7:
  - 4 committed developments with stated shares (2 Finsbury Ave 25%, Broadgate Tower 50%, 1 Appold St 50%, West One 25%);
  - 2 Canada Water buildings completed Q1 2026;
  - Euston Tower (consented).
- Landsec (FY26 results), 15:
  - Thirty High SW1 (total development cost £446m) and Republic, Manchester (£154m);
  - Timber Square (completed);
  - 3 retail schemes on site;
  - 9 pre-development consents or designs.
- SEGRO (H1 2026), 4: named completions and pre-lets. Its tables are regional totals only.
- Montea (Q3 2026), 4 under construction: Halle €34m, Tiel/Arjo €6m, DC Quartz €69m (linked to Codex's DC Quartz record), Skechers Liège (40% stake, €167m maximum exposure).
- WDP: the Q3 PDF returns HTTP 403, so no records. The WDP-ARGAN merger is noted: announced 23 Jul 2026, completion expected Q1 2027.
- Listings: British Land (UK-BLND on its own site) and Montea ("Euronext Brussels (MONT)") are verified. Landsec and SEGRO tickers are not stated in the fetched documents, so they stay research_only and are not shown in the UI.
- Not carried: ERV, rents, yields, market values, occupancy.
- Reuse for UK/EU company facts is pending (website terms not reviewed). Wikidata locations are CC0.

## 5. Importer, regression, performance
- Full chain on Codex's importer: Data Centers 602, then RE batch-1 765, then Phase 5B 767 (2 inserted, 158 updated, 5 retired), then JRE 811, then UK/EU 841. Each step took 0.5-0.75 s.
- Codex suites: 122 tests OK. Phase 5B tests: 14 OK.

## 6. UI (local branch `claude/realestate-projects`)
- 34 Real Estate records are shown (photo or plan, documented ticker): BXP 11, HST 10, BLND 7, MONT 4, JRE 2. 16 have photos.
- The Real Estate tab is ready in about 0.4 s. Energy (30 rows) and Data Centers (29 rows) are unchanged. No page errors. No sideways scroll on phone.
- First-visit test with the cookie banner left in place:
  - Desktop: the tabs can be clicked, but the banner covers the lower part of the detail panel and the stats bar.
  - Phone: the banner blocks the sector tabs until a choice is made. The #68 cookie fix is not on main; it is stashed.
  - Phone, existing behaviour (also on Energy): after expanding the list sheet, the first row sits under the bottom navigation bar.

## 7. Owner decisions and blockers
1. Approve or reject each of the 20 records in approval-manifest.json.
2. Reston Next Retail has only a city point; publish it as approximate, or wait for an address.
3. Reuse terms for JRE, British Land, Landsec, SEGRO and Montea company facts.
4. The #68 cookie fix (stashed) and the phone list-sheet overlap need a separate fix before any release.
5. Commons photos (5 US, 8 Japan) need another slow attempt on a later day.
