# Java API module

See the repository-root [README](../README.md) for current build/run instructions and the local recovery scope. This module is self-contained with its repository's saved snapshots and Worker contracts.

From this directory, use Java 21 to run `java -jar target/investedia-backend-0.1.0-SNAPSHOT.jar` after the repository's `mvn verify` succeeds. Default API: http://127.0.0.1:8080/. Saved prices, news, globe and ledger reads are available; live crypto and ingestion remain intentionally unavailable. Supabase is an external account service, not a Java-managed user database.

The migration documents under docs/ and VERIFICATION.md record the earlier monorepo work. They remain useful historical context; repository-root instructions and the workspace recovery verification describe the current split. No production deployment is configured.
