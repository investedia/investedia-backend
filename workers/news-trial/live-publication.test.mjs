import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { prepareLiveInputs, postLiveInputs } from "./live-publication.mjs";
import { ingestNews } from "../live/v1/news.js";
import { ingestConnections } from "../live/v1/connections.js";
import { ingestCalendar } from "../live/v1/calendar.js";
import { ingestLibrary } from "../live/v1/library.js";
const feed = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8"));
const connections = JSON.parse(await readFile(new URL("../../assets/globe/connections.json", import.meta.url), "utf8"));
const article = feed.stories[0], encode = value => new TextEncoder().encode(JSON.stringify(value));
const news = { generated_at: feed.updated_at, stories: feed.stories.slice(0, 2), stats: {} };
const days = { days: { [article.published_at.slice(0, 10)]: [{ id: article.id, h: article.headline, t: article.published_at, c: article.category }] } };
const env = { LIVE_INGEST_ENABLED: "true", LIVE_INGEST_TOKEN: "test-control" };
const inputs = () => ({ news: encode(news), connections: encode(connections), library: encode(days) });

test("real saved payloads pass the unchanged live API validators with token only in headers", async () => {
  const values = new Map(), calls = [], before = inputs(), original = structuredClone(before);
  const receiver = { INGEST_TOKEN: env.LIVE_INGEST_TOKEN, PRICES: { get: async key => values.get(key) ?? null, put: async (key, value) => values.set(key, value) } };
  const handlers = { "/v1/ingest/news": ingestNews, "/v1/ingest/connections": ingestConnections, "/v1/ingest/library": ingestLibrary };
  const result = await postLiveInputs(before, env, async (url, options) => {
    calls.push(url); assert.equal(new URL(url).origin, "https://api.investedia.com"); assert.equal(options.redirect, "manual");
    assert.equal(options.headers.Authorization, "Bearer test-control");
    assert.equal(new TextDecoder().decode(options.body).includes("test-control"), false);
    const outcome = await handlers[new URL(url).pathname](new Request(url, options), receiver);
    return Response.json(outcome.body, { status: outcome.status });
  });
  assert.equal(result.news.ok, true); assert.equal(result.connections.ok, true); assert.equal(result.library.ok, true);
  assert.equal(Object.hasOwn(result.news, "added"), false); assert.deepEqual(before, original);
  assert.deepEqual(calls.map(u => new URL(u).pathname), Object.keys(handlers));
  assert.ok(values.has("news"));
});
test("disabled, missing-token and invalid input sets make no network calls", async () => {
  const noFetch = () => { throw Error("must not call"); };
  for (const settings of [{}, { ...env, LIVE_INGEST_ENABLED: "false" }, { ...env, LIVE_INGEST_TOKEN: "" }, { ...env, LIVE_INGEST_TOKEN: "bad\nheader" }])
    await assert.rejects(postLiveInputs(inputs(), settings, noFetch));
  for (const body of [{ news: encode(news) }, { calendar: encode({}), news: encode(news) }, { ...inputs(), private: encode({}) },
    { ...inputs(), news: new Uint8Array(400001) }, { ...inputs(), library: new Uint8Array() }])
    await assert.rejects(postLiveInputs(body, env, noFetch));
});
test("redirects and bad acknowledgements never forward credentials or expose response details", async () => {
  for (const make of [() => new Response("private details", { status: 302, headers: { Location: "https://other.invalid/" } }),
    () => new Response("private details", { status: 503 }), () => Response.json({ ok: false, key: "private details" }),
    () => new Response("private details"), () => new Response("x".repeat(1024 * 1024 + 1))]) {
    let calls = 0;
    await assert.rejects(postLiveInputs(inputs(), env, async () => { calls++; return make(); }), error => {
      assert.equal(error.message, "Live news ingestion failed"); return true;
    }); assert.equal(calls, 1);
  }
});
test("compact-day sync remains best effort after required news and connections acknowledge", async () => {
  let calls = 0;
  const result = await postLiveInputs(inputs(), env, async () => ++calls === 3 ? new Response("failure", { status: 500 }) : Response.json({ ok: true, written: false }));
  assert.equal(result.news.ok, true); assert.equal(result.connections.ok, true); assert.deepEqual(result.library, { ok: false });
});
test("only bounded fixed producer exports can be prepared, with optional absent day listings", async () => {
  const calls = [];
  const data = { news, connections };
  const port = { fetch: async input => { const url = new URL(input); calls.push(url.searchParams.get("kind"));
    assert.equal(url.origin, "http://container"); assert.equal(url.pathname, "/output");
    const body = data[url.searchParams.get("kind")]; return body ? Response.json(body) : new Response("missing", { status: 404 });
  } };
  const body = await prepareLiveInputs(port, "news"); assert.deepEqual(Object.keys(body), ["news", "connections"]);
  assert.deepEqual(JSON.parse(new TextDecoder().decode(body.news)), news); assert.deepEqual(calls, ["news", "connections", "library"]);
  await assert.rejects(prepareLiveInputs(port, "markets"));
  await assert.rejects(prepareLiveInputs({ fetch: async () => new Response("x".repeat(400001)) }, "news"));
});
test("calendar uses its own fixed authenticated endpoint", async () => {
  const calendar = JSON.parse(await readFile(new URL("../../assets/calendar-live.json", import.meta.url), "utf8"));
  const body = encode(calendar); let calls = 0; const stored = new Map();
  const result = await postLiveInputs({ calendar: body }, env, async (url, options) => {
    calls++; assert.equal(url, "https://api.investedia.com/v1/ingest/calendar"); assert.equal(options.headers.Authorization, "Bearer test-control");
    const receiver = { INGEST_TOKEN: "test-control", PRICES: { put: async (key, value) => stored.set(key, value) } };
    const outcome = await ingestCalendar(new Request(url, options), receiver);
    return Response.json(outcome.body, { status: outcome.status });
  }); assert.equal(calls, 1); assert.equal(result.calendar.ok, true); assert.ok(result.calendar.count > 0); assert.ok(stored.has("calendar"));
});


test("runtime transport requires the configured private live service, with no public fetch fallback", async () => {
  await assert.rejects(postLiveInputs(inputs(), env), /binding missing/);
  const calls = [];
  const service = { fetch: async (url, options) => { calls.push(url); assert.equal(options.headers.Authorization, "Bearer test-control"); return Response.json({ ok: true }); } };
  const result = await postLiveInputs(inputs(), { ...env, LIVE_API: service });
  assert.equal(result.news.ok, true); assert.equal(calls.length, 3);
});


test("ingest failure diagnostics contain only fixed kinds and HTTP numbers", async () => {
  const captured = [], original = console.warn;
  console.warn = (...args) => captured.push(args);
  try {
    await assert.rejects(postLiveInputs(inputs(), env, async () => new Response("private response must never be logged", { status: 409 })));
    assert.deepEqual(captured, [["live_ingest_failure", JSON.stringify({ kind: "news", http_status: 409 })]]);
  } finally { console.warn = original; }
});


test("transient immutable export reads retry once without producer runs or byte changes", async () => {
  for (const mode of ["network", "stream", "server"]) {
    const data = inputs(), calls = []; let failed = false;
    const port = { fetch: async input => {
      const url = new URL(input), kind = url.searchParams.get("kind");
      assert.equal(url.origin, "http://container"); assert.equal(url.pathname, "/output"); calls.push(kind);
      if (kind === "news" && !failed) {
        failed = true;
        if (mode === "network") throw Error("private transport details");
        if (mode === "server") return new Response("private provider body", { status: 503 });
        return new Response(new ReadableStream({ start(controller) { controller.error(Error("private stream details")); } }));
      }
      return new Response(data[kind]);
    } };
    const body = await prepareLiveInputs(port, "news");
    assert.deepEqual(calls, ["news", "news", "connections", "library"]);
    for (const kind of Object.keys(data)) assert.deepEqual(body[kind], data[kind]);
  }
});

test("persistent export failures stop after two reads with fixed non-secret diagnostics", async () => {
  let calls = 0; const original = console.warn, logs = []; console.warn = (...args) => logs.push(args);
  try {
    await assert.rejects(prepareLiveInputs({ fetch: async () => { calls++; throw Error("private transport must never leak"); } }, "news"), /Live export news failed/);
  } finally { console.warn = original; }
  assert.equal(calls, 2); assert.equal(logs.length, 2);
  assert.deepEqual(logs.map(([name]) => name), ["live_export_retry", "live_export_failure"]);
  assert.equal(JSON.stringify(logs).includes("private transport"), false);
  for (const [, text] of logs) assert.deepEqual(Object.keys(JSON.parse(text)).sort(), ["attempt", "http_status", "kind", "reason"]);
  assert.deepEqual(JSON.parse(logs[1][1]), { kind: "news", http_status: 0, reason: "unavailable", attempt: 2 });
});

test("oversized exports and required HTTP 404 are never retried or partially accepted", async () => {
  for (const mode of ["oversized", "missing"]) {
    let calls = 0; const original = console.warn, logs = []; console.warn = (...args) => logs.push(args);
    try {
      await assert.rejects(prepareLiveInputs({ fetch: async () => { calls++; return mode === "oversized" ? new Response("x".repeat(400001)) : new Response("private missing body", { status: 404 }); } }, "news"));
    } finally { console.warn = original; }
    assert.equal(calls, 1); assert.equal(logs.length, 1);
    const record = JSON.parse(logs[0][1]); assert.equal(record.reason, mode === "oversized" ? "oversized" : "http_rejected");
    assert.equal(JSON.stringify(logs).includes("private missing"), false);
  }
});

test("optional compact-day export failure stays best effort without sending invalid data", async () => {
  for (const mode of ["oversized", "server"]) {
    const data = inputs(), calls = [];
    const original = console.warn, logs = []; console.warn = (...args) => logs.push(args);
    let prepared;
    try {
      prepared = await prepareLiveInputs({ fetch: async url => {
        const kind = new URL(url).searchParams.get("kind"); calls.push(kind);
        return kind === "library" ? mode === "oversized" ? new Response("x".repeat(900001)) : new Response("private optional failure", { status: 503 }) : new Response(data[kind]);
      } }, "news");
    } finally { console.warn = original; }
    assert.deepEqual(Object.keys(prepared), ["news", "connections"]);
    assert.equal(calls.filter(kind => kind === "library").length, mode === "oversized" ? 1 : 2);
    assert.equal(logs.at(-1)[0], "live_export_failure"); assert.equal(JSON.parse(logs.at(-1)[1]).kind, "library");
    assert.equal(JSON.stringify(logs).includes("private optional"), false);
    const sent = [];
    const result = await postLiveInputs(prepared, env, async url => { sent.push(url); return Response.json({ ok: true, written: false }); });
    assert.equal(result.news.ok, true); assert.equal(result.connections.ok, true);
    assert.equal(sent.some(url => url.endsWith("/library")), false);
  }
});

test("required connections still fail immediately above the unchanged receiver bound", async () => {
  const calls = [];
  await assert.rejects(prepareLiveInputs({ fetch: async url => {
    const kind = new URL(url).searchParams.get("kind"); calls.push(kind);
    return new Response(kind === "news" ? inputs().news : new Uint8Array(2 * 1024 * 1024 + 1));
  } }, "news"));
  assert.deepEqual(calls, ["news", "connections"]);
});
