import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const text = (await readFile(new URL("../../.github/workflows/export-news-trial-seed.yml", import.meta.url), "utf8")).replace(/\r\n/g, "\n");
const script = text.split("          script: |\n")[1].split("      - name: Restore exact")[0]
  .split("\n").map(line => line.replace(/^ {12}/, "")).join("\n");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const select = new AsyncFunction("github", "context", "core", script);

test("export selects the exact successful priority run and attempt, without a broad cache fallback", async () => {
  let selected;
  const github = { rest: { actions: { listWorkflowRuns: async options => {
    assert.deepEqual(options, { owner: "investedia", repo: "investedia-backend", workflow_id: "priority-news.yml", branch: "main", status: "success", per_page: 1 });
    return { data: { workflow_runs: [{ id: 123, run_attempt: 2 }] } };
  } } } };
  await select(github, { repo: { owner: "investedia", repo: "investedia-backend" } }, {
    setOutput: (name, value) => { assert.equal(name, "cache-key"); selected = value; },
  });
  assert.equal(selected, "priority-news-state-123-2");
  assert.ok(text.includes("key: ${{ steps.producer.outputs.cache-key }}"));
  assert.equal(text.includes("restore-keys:"), false);
});
test("export fails closed when there is no successful priority run", async () => {
  await assert.rejects(() => select({ rest: { actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: [] } }) } } },
    { repo: { owner: "investedia", repo: "investedia-backend" } }, { setOutput: () => assert.fail("must not select") }), /No successful priority/);
});
