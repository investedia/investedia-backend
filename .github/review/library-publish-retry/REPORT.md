# Article-library publisher retry identity

Pre-existing failure: backend run 44946506185, publish job 136974904313, failed on 21 November before the owner's merges of frontend #219 and backend #102. Article generation succeeded. A competing frontend push rejected the first push; `git pull --rebase` then failed because the runner had no Git identity. The original workflow supplied identity only to the first commit command.

Fix: configure the same existing robot name/email locally in the frontend checkout before staging. Both the initial commit and any rebase now inherit the identity. Retry counts, authentication, schedules, article contents and timestamp handling are unchanged. No live job was retried or dispatched during verification.

Files: `.github/workflows/publish-library.yml`; required generated knowledge-graph outputs `graphify-out/graph.json`, `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`; this report and `result.json`.

Validation: executed the exact fixed workflow block against disposable local Git repositories with a real competing push and global identity disabled. The first push was rejected, rebase/retry succeeded, both changes survived and the local remote matched the publisher. The original workflow reproduced the missing-identity failure in the same fixture setup. No external services were used for these tests. All 4 publisher unit tests, 101 Worker tests and 13 Java/API contract checks pass. `git diff --check` passes. No article, market, ledger, auth, schema, secret or runtime source changes.

Required `graphify update .` passed in code-only mode, without model/API calls: 2,966 nodes and 5,839 edges. It reported that four SQL files are not indexed because the optional SQL parser is missing; no dependency was installed. Existing Java deprecation/agent warnings remain. No new failing checks.

Draft fix only. No merge, deployment, robot switch or live article publication was performed by this task.
