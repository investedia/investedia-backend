import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { destination, egress, route } from "./policy.mjs";

test("egress rejects production, secrets in URLs, non-HTTPS and all non-Gemini writes", () => {
  for (const url of ["https://api.investedia.com/v1/news/ingest", "https://127.0.0.1/", "http://www.ecb.europa.eu/",
    "https://www.ecb.europa.eu:8443/", "https://user:pass@www.ecb.europa.eu/", "https://www.ecb.europa.eu.evil.invalid/"])
    assert.equal(destination(url, "GET"), null);
  assert.equal(destination("https://www.ecb.europa.eu/rss", "POST"), null);
  assert.equal(destination("https://generativelanguage.googleapis.com/v1beta/models/flash:generateContent?key=x", "POST"), null);
  assert.equal(destination("https://www.ecb.europa.eu/rss", "GET"), "source");
});
test("redirects cannot escape allowlist, publisher requests receive no credentials", async () => {
  let calls = 0;
  const response = await egress(new Request("https://www.ecb.europa.eu/rss", { headers: { Authorization: "private", "x-goog-api-key": "private" } }),
    "test-key", true, async (url, init) => {
      calls++;
      assert.equal(init.headers.get("Authorization"), null);
      assert.equal(init.headers.get("x-goog-api-key"), null);
      assert.equal(init.redirect, "manual");
      return new Response(null, { status: 302, headers: { location: "https://api.investedia.com/" } });
    });
  assert.equal(response.status, 403);
  assert.equal(calls, 1);
});
test("only Gemini receives the proxy key; errors never echo upstream details", async () => {
  const response = await egress(new Request("https://generativelanguage.googleapis.com/v1beta/models/flash:generateContent", { method: "POST", body: "{}" }),
    "test-key", true, async (url, init) => {
      assert.equal(init.headers.get("x-goog-api-key"), "test-key");
      return new Response("sensitive upstream details", { status: 400 });
    });
  assert.equal(response.status, 400);
  assert.equal(await response.text(), "Trial upstream failed");
});
test("disabled egress and unauthenticated/default-disabled routes make no binding calls", async () => {
  const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "false" };
  assert.equal((await egress(new Request("https://www.ecb.europa.eu/"), "test-key", false, () => { throw Error("must not fetch"); })).status, 403);
  assert.equal((await route(new Request("https://trial/run", { method: "POST" }), env)).status, 401);
  assert.equal((await route(new Request("https://trial/run", { method: "POST", headers: { Authorization: "Bearer test-token" } }), env)).status, 409);
  assert.equal((await route(new Request("https://trial/run", { method: "POST", headers: { Authorization: "Bearer undefined" } }), {})).status, 401);
});

// Exercise the real orchestration with platform bindings replaced, not the producer.
const source = (await readFile(new URL("./index.js", import.meta.url), "utf8"))
  .replace('import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";',
    'class DurableObject { constructor(ctx, env) { this.ctx=ctx; this.env=env; } } class WorkerEntrypoint {}')
  .replace('"./policy.mjs"', JSON.stringify(new URL("./policy.mjs", import.meta.url).href));
const { NewsTrial } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
function bindings(fail = false) {
  const puts = [], starts = [];
  const c = { running: false, images: { base: "image" },
    start(options) { starts.push(options); this.running = true; },
    async setInactivityTimeout() {}, async interceptOutboundHttps(host) { assert.equal(host, "*"); },
    getTcpPort() { return { fetch: async url => url.endsWith("/health") ? new Response() : fail
      ? new Response("failed", { status: 422 }) : Response.json({ files: {}, summary: { trial: true } }) }; },
    async destroy() { this.running = false; } };
  const env = { TRIAL_ENABLED: "true", GEMINI_API_KEY: "test-key", TRIAL_STORE: {
    get: async name => name.endsWith("seed.json") ? { size: 2, arrayBuffer: async () => new TextEncoder().encode("{}") } : null,
    put: async (name, value) => puts.push(name),
  } };
  return { instance: new NewsTrial({ container: c, exports: { TrialEgress: () => ({}) } }, env), c, puts, starts };
}
test("successful trial stores only isolated artifacts and stops the container", async () => {
  const b = bindings();
  assert.equal((await b.instance.fetch()).status, 200);
  assert.deepEqual(b.puts, ["trial/latest.json", "trial/state.json"]);
  assert.equal(b.starts[0].enableInternet, false);
  assert.equal(b.starts[0].env, undefined);
  assert.equal(b.c.running, false);
});
test("producer failure retains previous state and always stops container", async () => {
  const b = bindings(true);
  assert.equal((await b.instance.fetch()).status, 502);
  assert.deepEqual(b.puts, []);
  assert.equal(b.c.running, false);
});
test("overlapping requests cannot start a second container", async () => {
  const b = bindings();
  const first = b.instance.fetch();
  assert.equal((await b.instance.fetch()).status, 409);
  await first;
  assert.equal(b.starts.length, 1);
});
