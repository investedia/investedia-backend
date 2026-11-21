# Preserve useful work from backend PRs #20 and #22

Replaces the obsolete coverage-audit and news-connections drafts on current main.

Kept: optional, bounded, read-only API fetch support; accurate saved-file/API provenance and input hashes; explicit opt-in for diagnostic fallback; the three missing resolver tests. Added six audit-input checks covering provenance, fallback, argument ambiguity, HTTPS validation, redirects and response limits.

Already on main: the core country audit and explicit-impact resolver. Not copied: stale generated reports, empty licence manifests, old workflow changes or production resolver wiring. No new links are enabled, no jobs run and no data files change.

Files: `tools/coverage/audit.py`, `tests/test_coverage_audit.py`, `tests/test_coverage_connections.py`, this report.

Validation: 8 audit tests and 3 connection tests pass, with no real network calls; all 101 Worker tests pass; `mvnw.cmd -B -ntp verify` passes all 13 Java checks and API/Worker contracts; diff whitespace checks pass. Existing Java deprecation/agent warnings remain. No failing checks. Live API availability was not tested.

This branch is a draft replacement, not a deployment. The old PR branches retain their original history and reports.
