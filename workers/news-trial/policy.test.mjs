import test from "node:test";
import { gzipSync } from "node:zlib";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { destination, egress, route, trialTier, trialJob, safeDiagnostic } from "./policy.mjs";

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
    async setInactivityTimeout() {}, async interceptAllOutboundHttp() {}, async interceptOutboundHttps(host) { assert.equal(host, "*"); },
    getTcpPort() { return { fetch: async url => {
      if (url.endsWith("/health")) return new Response();
      if (fail) return new Response("failed", { status: 422 });
      const u = new URL(url);
      const summary = u.searchParams.get("job") === "calendar" ? { trial: true, job: "calendar" } : { trial: true, tier: u.searchParams.get("tier") || "priority" };
      return new Response(gzipSync(JSON.stringify({ files: {}, summary })), { headers: { "X-Trial-Summary": JSON.stringify(summary) } });
    } }; },
    async destroy() { this.running = false; } };
  const env = { TRIAL_ENABLED: "true", GEMINI_API_KEY: "test-key", TRIAL_STORE: {
    get: async name => name.endsWith("seed.json.gz") ? { size: 2, arrayBuffer: async () => new TextEncoder().encode("{}") } : null,
    put: async (name, value) => puts.push(name),
  } };
  return { instance: new NewsTrial({ container: c, exports: { TrialEgress: () => ({}) } }, env), c, puts, starts };
}
test("successful trial stores only isolated artifacts and stops the container", async () => {
  const b = bindings();
  assert.equal((await b.instance.fetch()).status, 200);
  assert.deepEqual(b.puts, ["trial/latest.json.gz", "trial/state.json.gz"]);
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

test("malformed compressed output or summary never advances state", async () => {
  for (const [body, header] of [["not gzip", '{"trial":true}'], [gzipSync("{}"), "invalid JSON"], [gzipSync("{}"), "x".repeat(4097)]]) {
    const b = bindings();
    b.c.getTcpPort = () => ({ fetch: async url => url.endsWith("/health") ? new Response() : new Response(body, { headers: { "X-Trial-Summary": header } }) });
    assert.equal((await b.instance.fetch()).status, 502);
    assert.deepEqual(b.puts, []);
    assert.equal(b.c.running, false);
  }
});

test("only the two fixed news tiers can reach a container", async () => {
  assert.equal(trialTier(new Request("https://trial/run")), "priority");
  assert.equal(trialTier(new Request("https://trial/run?tier=broad")), "broad");
  assert.equal(trialTier(new Request("https://trial/run?tier=../../other")), null);
  assert.equal(trialTier(new Request("https://trial/run?tier=priority&tier=broad")), null);
  let target;
  const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "true", GEMINI_API_KEY: "test-key", TRIAL_CONTAINER: {
    getByName: name => { assert.equal(name, "priority-trial"); return { fetch: async url => { target = url; return new Response(); } }; },
  } };
  const headers = { Authorization: "Bearer test-token" };
  assert.equal((await route(new Request("https://trial/run?tier=bad", { method: "POST", headers }), env)).status, 400);
  await route(new Request("https://trial/run?tier=broad", { method: "POST", headers }), env);
  assert.equal(target, "http://trial/run?tier=broad&job=news");
});
test("legacy HTTP feed requests are upgraded to HTTPS without opening arbitrary HTTP access", async () => {
  let target;
  const response = await egress(new Request("http://www.ecb.europa.eu/rss"), "test-key", true, async url => { target = url; return new Response("ok"); });
  assert.equal(response.status, 200);
  assert.equal(target, "https://www.ecb.europa.eu/rss");
  assert.equal((await egress(new Request("http://127.0.0.1/"), "test-key", true)).status, 403);
});
test("failure reports only a controlled stage and stops the container", async () => {
  const b = bindings(true);
  const response = await b.instance.fetch(new Request("http://trial/run?tier=broad"));
  assert.deepEqual(await response.json(), { error: "trial_failed", stage: "producer", tier: "broad", production_untouched: true });
  assert.deepEqual(b.puts, []);
});

test("calendar uses separate storage and a separate container without a Gemini key", async () => {
  assert.equal(trialJob(new Request("https://trial/run?job=calendar")), "calendar");
  assert.equal(trialJob(new Request("https://trial/run?job=../../other")), null);
  assert.equal(trialJob(new Request("https://trial/run?job=calendar&job=news")), null);
  let target;
  const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "true", TRIAL_CONTAINER: {
    getByName: name => { assert.equal(name, "calendar-trial"); return { fetch: async url => { target=url; return new Response(); } }; },
  } };
  const response = await route(new Request("https://trial/run?job=calendar", { method: "POST", headers: { Authorization: "Bearer test-token" } }), env);
  assert.equal(response.status, 200);
  assert.equal(target, "http://trial/run?tier=priority&job=calendar");
  const b=bindings(); await b.instance.fetch(new Request("http://trial/run?job=calendar"));
  assert.deepEqual(b.puts, ["trial/calendar/latest.json.gz", "trial/calendar/state.json.gz"]);
});
test("FRED gets only its own key and redirects cannot carry it elsewhere", async () => {
  let calls=0;
  const response = await egress(new Request("https://api.stlouisfed.org/fred/releases/dates?api_key=trial-proxy&file_type=json"), "", true,
    async (url, init) => { calls++; assert.equal(new URL(url).searchParams.get("api_key"), "test-fred"); assert.equal(init.headers.get("x-goog-api-key"), null); return new Response(null,{status:302,headers:{location:"https://www.ecb.europa.eu/"}}); }, "test-fred");
  assert.equal(response.status,502);assert.equal(calls,1);
  assert.equal(destination("https://api.stlouisfed.org/fred/series/observations", "POST"),null);
  assert.equal(destination("https://api.stlouisfed.org/private", "GET"),null);
});
test("diagnostics expose only bounded counters, booleans and HTTP codes", () => {
  const value={fetched:10,candidates:2,failed_source_count:1,gemini_ok:false,http_statuses:[429,401,"key",999],raw_key:"do-not-expose"};
  assert.deepEqual(safeDiagnostic(value),{fetched:10,candidates:2,failed_source_count:1,gemini_ok:false,http_statuses:[429,401]});
  assert.equal(safeDiagnostic({...value,fetched:-1}),null);
});

test("a result for another job cannot overwrite calendar state", async () => {
  const b=bindings();
  b.c.getTcpPort=()=>({fetch:async url=>url.endsWith("/health")?new Response():new Response(gzipSync("{}"),{headers:{"X-Trial-Summary":JSON.stringify({trial:true,tier:"priority"})}})});
  assert.equal((await b.instance.fetch(new Request("http://trial/run?job=calendar"))).status,502);
  assert.deepEqual(b.puts,[]);
});
