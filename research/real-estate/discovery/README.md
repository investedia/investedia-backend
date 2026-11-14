# Milestone 2 — discovery pool (14 Nov 2026)

- `sec-candidates.json`: 251 sentences from the latest annual reports (10-K / 20-F) of 56 US-listed issuers, each with URL, SHA-256, retrieval time. SEC accepted the declared User-Agent (owner-approved); no refusals. Not resolved on SEC: SEAS, ALEX, PLYA, SOHO (renamed/delisted — not assumed, to check).
- `pool.json`: **139 rows** = **37 `evidence_located`** (named development + filing locator) and **102 `lead_unverified`** (reminders from general knowledge; zero verified facts; confirm against the named primary source or drop).
- Six of the 37 are *competitor mentions* (Galaxy Phase 4, Londoner Grand, Solaire North, Westside City, Hard Rock Athens, MGM Osaka): the filing proves the project is discussed, not the investor's route. They need the owner's own filing.
- Low-materiality items seen and not pooled: routine room renovations (e.g. DiamondRock), generic "we may develop" language.

## Route notes for Milestone 3
- GLPI's Acorn Ridge loan is a **project loan held by a listed REIT**, not a bond a visitor can buy: route = indirect listed REIT, lender role.
- Bally's Chicago, Inc. is a possible **direct project equity** case (registered offering). Status, eligibility limits and whether it is still open must come from its own SEC filings; otherwise research-only.
- Lamda Development (Ellinikon) has listed bonds: check prospectus use-of-proceeds before calling anything project-specific.
- State/private owners (PIF, ICD, Katara, Mori Building, Chow Tai Fook Ent., Hinduja, Dajia…) → research only unless a documented listed instrument exists.

## Proposed contract addition (documented, not applied)
`extensions.real_estate.investment_route = {category: direct_project_equity | project_debt | issuer_debt | listed_equity | listed_reit | verified_fund | restricted_private | research_only, instrument: {issuer, identifier(ISIN/CUSIP), currency, maturity, status}, access: {open: bool|null, eligibility, jurisdiction, minimum}, as_of, evidence{}}`.
Importer `investment_access` stays one of its five existing values (bonds/direct offerings are imported as `research_only` there, with the real category only in the extension) until Codex/owner approve a contract change.
