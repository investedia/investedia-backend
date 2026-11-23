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
  .replace('"./policy.mjs"', JSON.stringify(new URL("./policy.mjs", import.meta.url).href))
  .replace('"./library.mjs"', JSON.stringify(new URL("./library.mjs", import.meta.url).href));
const { NewsTrial } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
function bindings(fail = false, articles = []) {
  const puts = [], starts = [];
  const c = { running: false, images: { base: "image" },
    start(options) { starts.push(options); this.running = true; },
    async setInactivityTimeout() {}, async interceptAllOutboundHttp() {}, async interceptOutboundHttps(host) { assert.equal(host, "*"); },
    getTcpPort() { return { fetch: async url => {
      if (url.endsWith("/health")) return new Response();
      if (new URL(url).pathname === "/library") { const cursor = Number(new URL(url).searchParams.get("cursor")); return Response.json({ articles: articles.slice(cursor, cursor + 10), next: Math.min(cursor + 10, articles.length), total: articles.length }); }
      if (fail) return new Response("failed", { status: 422 });
      const u = new URL(url);
      const summary = u.searchParams.get("job") && u.searchParams.get("job") !== "news" ? { trial: true, job: u.searchParams.get("job"), library_articles: articles.length } : { trial: true, tier: u.searchParams.get("tier") || "priority", library_articles: articles.length };
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
    async (url, init) => { calls++; assert.equal(new URL(url).searchParams.get("api_key"), "a".repeat(32)); assert.equal(init.headers.get("x-goog-api-key"), null); return new Response(null,{status:302,headers:{location:"https://www.ecb.europa.eu/"}}); }, "a".repeat(32));
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

test("FRED errors return fixed reasons without provider bodies or key values", async () => {
  const key = "a".repeat(32);
  const cases = [[400, "The value for variable api_key is not registered: " + key, "key_rejected"],
    [400, "Invalid realtime_end", "request_parameters"], [429, key, "rate_limited"], [503, key, "upstream_unavailable"], [400, key, "request_rejected"]];
  for (const [status, message, reason] of cases) {
    const response = await egress(new Request("https://api.stlouisfed.org/fred/releases/dates"), "", true,
      async () => Response.json({ error_message: message }, { status }), key);
    const body = await response.text(); assert.deepEqual(JSON.parse(body), { trial_fred_reason: reason }); assert.equal(body.includes(key), false);
  }
});
test("FRED key format fails before network and surrounding whitespace is normalized", async () => {
  let calls=0;
  const upstream=async url=>{calls++;assert.equal(new URL(url).searchParams.get("api_key"),"a".repeat(32));return Response.json({ok:true});};
  const bad=await egress(new Request("https://api.stlouisfed.org/fred/releases/dates"),"",true,upstream,"not-a-key");
  assert.deepEqual(await bad.json(),{trial_fred_reason:"key_format"});assert.equal(calls,0);
  assert.equal((await egress(new Request("https://api.stlouisfed.org/fred/releases/dates"),"",true,upstream,"  "+"a".repeat(32)+"\n")).status,200);
  assert.equal(calls,1);
});

test("malformed or oversized provider errors stay generic and bounded", async () => {
  for (const raw of ["not JSON", JSON.stringify({error_message:"x".repeat(20000)})]) {
    const response=await egress(new Request("https://api.stlouisfed.org/fred/releases/dates"),"",true,async()=>new Response(raw,{status:400}),"a".repeat(32));
    assert.deepEqual(await response.json(),{trial_fred_reason:"request_rejected"});
  }
});


test("data jobs use independent state without requiring AI credentials", async () => {
  for (const job of ["markets", "fx", "economy-history", "country-basics"]) {
    const b = bindings();
    delete b.instance.env.GEMINI_API_KEY;
    assert.equal((await b.instance.fetch(new Request(`https://trial/run?job=${job}`))).status, 200);
    assert.deepEqual(b.puts, [`trial/${job}/latest.json.gz`, `trial/${job}/state.json.gz`]);
    assert.equal(b.c.running, false);
    let name;
    const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "true", TRIAL_CONTAINER: {
      getByName: value => { name = value; return { fetch: async () => new Response() }; },
    } };
    assert.equal((await route(new Request(`https://trial/run?job=${job}`, { method: "POST", headers: { Authorization: "Bearer test-token" } }), env)).status, 200);
    assert.equal(name, `${job}-trial`);
  }
});
test("data providers allow only fixed read-only API paths and receive no credentials", async () => {
  for (const url of ["https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json", "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=1mo&interval=1d"]) {
    assert.equal(destination(url, "GET"), "source");
    assert.equal(destination(url, "POST"), null);
    const response = await egress(new Request(url, { headers: { Authorization: "private" } }), "", true, async (target, init) => {
      assert.equal(init.headers.get("Authorization"), null);
      assert.equal(init.headers.get("x-goog-api-key"), null);
      return new Response("ok");
    });
    assert.equal(response.status, 200);
  }
  for (const url of ["https://api.worldbank.org/admin", "https://query1.finance.yahoo.com/account", "https://query2.finance.yahoo.com/v8/finance/chart/x"])
    assert.equal(destination(url, "GET"), null);
});


test("library export failure keeps the previous producer state and stops the container", async () => {
  const b = bindings();
  b.c.getTcpPort = () => ({ fetch: async url => {
    const path = new URL(url).pathname;
    if (path === "/health") return new Response();
    if (path === "/library") return new Response("unavailable", { status: 500 });
    const summary = { trial: true, tier: "priority", library_articles: 1 };
    return new Response(gzipSync("{}"), { headers: { "X-Trial-Summary": JSON.stringify(summary) } });
  } });
  const response = await b.instance.fetch();
  assert.equal(response.status, 502);
  assert.equal((await response.json()).stage, "library");
  assert.deepEqual(b.puts, []);
  assert.equal(b.c.running, false);
});

test("saved library transfer requires no AI key and shares the news lock", async () => {
  const b = bindings(); delete b.instance.env.GEMINI_API_KEY;
  assert.equal((await b.instance.fetch(new Request("https://trial/run?job=library"))).status, 200);
  assert.deepEqual(b.puts, ["trial/library/latest.json.gz", "trial/library/state.json.gz"]);
  let lock;
  const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "true", TRIAL_CONTAINER: {
    getByName: name => { lock = name; return { fetch: async () => new Response() }; },
  } };
  const response = await route(new Request("https://trial/run?job=library", { method: "POST", headers: { Authorization: "Bearer test-token" } }), env);
  assert.equal(response.status, 200); assert.equal(lock, "priority-trial");
});


test("article pages reacquire container ports after a closed producer response", async () => {
  const b = bindings();
  const rows = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8")).stories.slice(0, 2);
  let handles = 0;
  b.instance.env.TRIAL_STORE.head = async () => null;
  b.c.getTcpPort = () => {
    handles++; let closed = false;
    return { fetch: async url => {
      const u = new URL(url);
      if (u.pathname === "/health") return new Response();
      if (closed) throw new Error("Network connection lost");
      closed = true;
      if (u.pathname === "/run") {
        const summary = { trial: true, tier: "priority", library_articles: rows.length };
        return new Response(gzipSync("{}"), { headers: { "X-Trial-Summary": JSON.stringify(summary) } });
      }
      const cursor = Number(u.searchParams.get("cursor"));
      return Response.json({ articles: [rows[cursor]], next: cursor + 1, total: rows.length });
    } };
  };
  assert.equal((await b.instance.fetch()).status, 200);
  assert.equal(handles, 3);
  assert.deepEqual(b.puts, [...rows.map(row => `trial/library/articles/${row.id}.json`), "trial/latest.json.gz", "trial/state.json.gz"]);
  assert.equal(b.c.running, false);
});


test("publication requires its separate flag and bearer authentication", async () => {
  const b = bindings();
  assert.equal((await b.instance.fetch(new Request("http://trial/publish-library"))).status, 409);
  const request = new Request("https://trial/publish-library", { method: "POST", headers: { Authorization: "Bearer test-token" } });
  const env = { TRIAL_TOKEN: "test-token", TRIAL_ENABLED: "false" };
  assert.equal((await route(request, env)).status, 409);
  assert.equal((await route(new Request("https://trial/publish-library", { method: "POST" }), { ...env, PUBLISH_LIBRARY_ENABLED: "true" })).status, 401);
  let target;
  env.PUBLISH_LIBRARY_ENABLED = "true";
  env.TRIAL_CONTAINER = { getByName: name => { assert.equal(name, "priority-trial"); return { fetch: async (url, init) => { target = [url, init.method]; return new Response(); } }; } };
  assert.equal((await route(request, env)).status, 200);
  assert.deepEqual(target, ["http://trial/publish-library", "POST"]);
});
test("publication checkpoints completed pages, preserves bytes and starts no container", async () => {
  const b = bindings();
  b.instance.env.PUBLISH_LIBRARY_ENABLED = "true"; b.instance.env.TRIAL_ENABLED = "false";
  const rows = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8")).stories.slice(0, 2);
  const objects = new Map(rows.map(row => [`trial/library/articles/${row.id}.json`, JSON.stringify(row)]));
  const checkpoints = new Map();
  b.instance.ctx.storage = { get: async key => checkpoints.get(key), put: async (key, value) => checkpoints.set(key, value), delete: async key => checkpoints.delete(key) };
  b.instance.env.TRIAL_STORE = {
    head: async key => objects.has(key) ? {} : null,
    get: async key => objects.has(key) ? { size: objects.get(key).length, text: async () => objects.get(key) } : null,
    put: async (key, value) => objects.set(key, value),
    list: async options => { const row = rows[options.cursor ? 1 : 0]; return { objects: [{ key: `trial/library/articles/${row.id}.json`, size: 1 }], truncated: !options.cursor, cursor: options.cursor ? undefined : "next-page" }; },
  };
  const request = new Request("http://trial/publish-library", { method: "POST" });
  const first = b.instance.fetch(request);
  assert.equal((await b.instance.fetch(request)).status, 409);
  assert.deepEqual(await (await first).json(), { examined: 1, written: 1, done: false });
  assert.equal(checkpoints.get("library:publish:cursor"), "next-page");
  assert.deepEqual(await (await b.instance.fetch(request)).json(), { examined: 1, written: 1, done: true });
  assert.equal(checkpoints.size, 0);
  for (const row of rows) assert.equal(objects.get(`published/library/articles/${row.id}.json`), JSON.stringify(row));
  assert.equal((await (await b.instance.fetch(request)).json()).written, 0);
  assert.equal((await (await b.instance.fetch(request)).json()).written, 0);
  assert.equal(b.starts.length, 0); assert.equal(b.instance.busy, false);
});
test("failed publication retains its checkpoint and returns no raw exception", async () => {
  const b = bindings(); b.instance.env.PUBLISH_LIBRARY_ENABLED = "true";
  const changes = [];
  b.instance.ctx.storage = { get: async () => "saved-checkpoint", put: async (...args) => changes.push(args), delete: async (...args) => changes.push(args) };
  b.instance.env.TRIAL_STORE.list = async () => { throw Error("private provider response"); };
  const response = await b.instance.fetch(new Request("http://trial/publish-library", { method: "POST" }));
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: "article_publication_failed", existing_articles_preserved: true });
  assert.deepEqual(changes, []); assert.equal(b.starts.length, 0); assert.equal(b.instance.busy, false);
});

test("enabled news publication uses the validated saved copy before advancing state", async () => {
  const rows = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8")).stories.slice(0, 2);
  const b = bindings(false, rows), objects = new Map();
  b.instance.env.PUBLISH_LIBRARY_ENABLED = "true";
  b.instance.env.TRIAL_STORE.head = async key => objects.has(key) ? {} : null;
  b.instance.env.TRIAL_STORE.get = async key => key.endsWith("seed.json.gz") ? { size: 2, arrayBuffer: async () => new TextEncoder().encode("{}") }
    : objects.has(key) ? { size: new TextEncoder().encode(objects.get(key)).length, text: async () => objects.get(key) } : null;
  b.instance.env.TRIAL_STORE.put = async (key, value) => { objects.set(key, value); b.puts.push(key); };
  const response = await b.instance.fetch();
  assert.equal(response.status, 200);
  assert.equal((await response.json()).published_articles_written, rows.length);
  for (const row of rows) assert.equal(objects.get(`published/library/articles/${row.id}.json`), objects.get(`trial/library/articles/${row.id}.json`));
  assert.deepEqual(b.puts.slice(-2), ["trial/latest.json.gz", "trial/state.json.gz"]);
  const health = await route(new Request("https://trial/health", { headers: { Authorization: "Bearer test-token" } }), { TRIAL_TOKEN: "test-token", PUBLISH_LIBRARY_ENABLED: "true" });
  assert.equal((await health.json()).publication_enabled, true);
});


test("news provider failures log fixed categories without messages, keys or prompts", async () => {
  const captured = [], original = console.log;
  console.log = (...args) => captured.push(args);
  try {
    const cases = [
      [503, "UNAVAILABLE", "model overloaded never-log-this", "model_capacity"],
      [400, "INVALID_ARGUMENT", "API key not valid never-log-this", "key_rejected"],
      [400, "FAILED_PRECONDITION", "region not supported never-log-this", "region_restricted"],
      [429, "RESOURCE_EXHAUSTED", "quota exceeded never-log-this", "quota_or_rate_limit"],
      [400, "FAILED_PRECONDITION", "Billing is not enabled never-log-this", "billing_restricted"],
      [403, "PERMISSION_DENIED", "not permitted never-log-this", "permission_denied"],
      [400, "INVALID_ARGUMENT", "invalid request never-log-this", "request_invalid"],
      [503, "PRIVATE_STATUS", "unavailable never-log-this", "upstream_unavailable"],
      [503, "UNAVAILABLE", "details https://example.invalid/region/not-supported?key=never-log-this", "upstream_unavailable"],
    ];
    for (const [status, provider, message, reason] of cases) {
      const response = await egress(new Request("https://generativelanguage.googleapis.com/v1beta/models/flash:generateContent", { method: "POST", body: "private-prompt" }),
        "private-key", true, async () => Response.json({ error: { status: provider, message } }, { status }));
      assert.equal(response.status, status); assert.equal(await response.text(), "Trial upstream failed");
      const record = captured.at(-1); assert.equal(record[0], "news_provider_failure");
      const diagnostic = JSON.parse(record[1]);
      assert.equal(diagnostic.reason, reason);
      assert.equal(diagnostic.provider_status, provider === "PRIVATE_STATUS" ? "unknown" : provider);
      assert.equal(diagnostic.http_status, status);
    }
    assert.doesNotMatch(JSON.stringify(captured), /never-log-this|private-key|private-prompt|PRIVATE_STATUS/);
  } finally { console.log = original; }
});
test("malformed and oversized news-provider errors stay bounded and unreadable", async () => {
  const captured = [], original = console.log; console.log = (...args) => captured.push(args);
  try {
    let cancelled = false;
    const huge = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode("x".repeat(17000))); }, cancel() { cancelled = true; } });
    for (const body of ["<html>never-log-this</html>", huge]) {
      const response = await egress(new Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"), "private-key", true, async () => new Response(body, { status: 503 }));
      assert.equal(response.status, 503);
      assert.equal(JSON.parse(captured.at(-1)[1]).reason, "unreadable_provider_error");
    }
    assert.equal(cancelled, true);
    assert.doesNotMatch(JSON.stringify(captured), /never-log-this|private-key/);
  } finally { console.log = original; }
});
test("successful provider requests retain their response without failure logging", async () => {
  const original = console.log, captured = []; console.log = (...args) => captured.push(args);
  try {
    const response = await egress(new Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"), "private-key", true, async () => Response.json({ models: [] }));
    assert.deepEqual(await response.json(), { models: [] }); assert.deepEqual(captured, []);
  } finally { console.log = original; }
});
