# Proposed identity model — no registry built

Not investment advice.

Use separate immutable internal record IDs and versioned source assertions:

| Record | Meaning | Identity / relationships |
|---|---|---|
| legal_entity | Registered legal person | LEI where valid, national registration authority + company number, typed CIK/QID cross-references |
| issuer | Role issuing listed instruments | Links to legal_entity; SEC filer CIK when applicable; not one record per ticker |
| security | Specific instrument/share class | ISIN first; security-scoped QID as a lower-confidence cross-reference; issuer_id; validated type=common_stock initially |
| listing | A security traded on a venue in a currency | security_id + segment MIC + ticker + valid_from/to; ticker reuse tracked; same ISIN can have several listings |
| exchange | Trading venue | MIC, segment/operating relationship, country, IANA zone, provenance-backed sessions |

Stocks first. ETFs, bonds, depositary receipts, preferreds/units/warrants and
ambiguous instruments stay unavailable until separately classified/validated.
A corporate name does not establish the security class. Sector mappings keep
the source vocabulary and taxonomy/version; SIC is not silently relabelled GICS.

## Matching rules

Priority **ISIN > LEI > CIK > QID applies at the appropriate record level**.
ISIN identifies a security, not a legal entity. LEI/CIK on a security normally
identify its issuer and cannot equate all that issuer's share classes. QIDs are
typed (entity vs security vs exchange). Never join different record types merely
because an identifier string appears in both.

Validate ISIN checksum, LEI mod-97/format, padded CIK and QID/MIC syntax. Valid
syntax is not evidence that a code is allocated, fresh, or belongs to that asset.
An exact authoritative listing statement can verify a MIC+ticker observation
without inventing an ISIN, but cannot prove cross-listing identity. Names are
candidate-search text only, never a merge key. No independent-array cross-product.

Any contradictory valid identifier quarantines the match, even if another
identifier agrees. Keep both source assertions and reasons; do not overwrite
one with the highest-priority field or pick a convenient winner. Handle source
corrections, issuer renames, ticker reuse, mergers and delistings as dated events.
HQ requires an explicitly reported HQ assertion; SEC business address, legal
registered office and exchange/capital coordinates are distinct location kinds.

## Provenance and visibility

Every assertion: source, source_id, source_url, retrieved_at, source_updated_at,
valid_from/to, licence_id/version, validation_status, reason and evidence hash.
Each public record: verification_status (verified/unverified/conflicted/rejected),
stale independently, updated_at and source summaries. Missing values are null
with a machine-readable reason; never synthetic zero or inferred coordinates.

Default listing visibility is verified only. `hidden_unverified` counts eligible
unverified/conflicted common-stock rows under the SAME filters/snapshot before
that visibility filter; rejected rows never appear. Explicit inclusion labels
every row. Licence-cleared freshness and listing identity, not a colourful badge,
determine eligibility. Keep a per-country coverage status and denominator scope.
No production registry is written by this audit; tests exercise only matching
rules on small, clearly labelled reference fixtures.
