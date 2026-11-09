# Independent backend verification

Run from `backend/` with Java 21, Maven and Node 20+ installed:

```sh
mvn verify
```

Contract tests also require this checkout's `workers/live/v1/` modules and saved input snapshots. They do not contact production or write financial files.

The single [Maven transcript](evidence/maven-verify.log) is intentional task evidence. It records the actual verification command, tested source revision and result. Machine-specific paths are redacted; the unmodified original is retained outside the repository. The transcript is intentional test evidence under backend/evidence/, outside the GitHub Pages root. backend/.gitignore allows this one named log and continues ignoring other runtime logs. backend/.gitattributes enforces text with LF endings. The root ignore file does not ignore *.log, so no root exception is needed.

See the [numbered criteria/status/evidence table](../design/CODEX-TASK-JAVA-BACKEND.md). This backend-only change has no UI, mockup or browser-screenshot claim. Prices and news are saved snapshots, not live feeds. Not investment advice.

## Not done

Local read-only prototype only. Live crypto, ingestion/writes, production auth integration, full Worker parity and deployment remain deferred. No merge or deployment is authorized or performed.
