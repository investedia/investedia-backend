import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishIndexExports, publishedIds, readIndexInput, validateIndexManifest } from "./index-publication.mjs";
import { route } from "./policy.mjs";
const rows = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8")).stories.slice(0, 2);
const sha = body => createHash("sha256").update(body).digest("hex");
function fixture() {
  const objects = { "all.json": JSON.stringify(rows), "meta.json": JSON.stringify({ total: rows.length }) };
  const manifest = { version: sha(JSON.stringify(objects)), baseline_sha256: sha("baseline"),
    files: Object.fromEntries(Object.entries(objects).map(([name, body]) => [name, { size: Buffer.byteLength(body), sha256: sha(body) }])),
    pages: [[1, Buffer.byteLength(objects["all.json"]) - 2]] };
  manifest.version = sha(JSON.stringify(manifest.files));
  objects["manifest.json"] = JSON.stringify(manifest); objects["state.json.gz"] = new Uint8Array([31, 139]);
  const files = new Map(), writes = [], requests = [];
  const store = {
    get: async key => files.has(key) ? { size: files.get(key).body.byteLength, text: async () => new TextDecoder().decode(files.get(key).body) } : null,
    head: async key => files.has(key) ? { size: files.get(key).body.byteLength, customMetadata: files.get(key).options.customMetadata } : null,
    put: async (key, body, options) => { writes.push(key); files.set(key, { body: typeof body === "string" ? new TextEncoder().encode(body) : body, options }); }
  };
  const port = { fetch: async input => { const u = new URL(input); requests.push(u.searchParams.get("file")); return new Response(objects[u.searchParams.get("file")]); } };
  return { objects, manifest, files, writes, requests, store, port };
}

test("complete checksummed index is committed last, repeat publication writes nothing", async () => {
  const f = fixture();
  assert.deepEqual(await publishIndexExports(f.port, f.store), { version: f.manifest.version, written: 2 });
  assert.equal(f.writes.at(-1), "published/library-index/current.json");
  assert.equal(f.writes.at(-2), "trial/library-index/state.json.gz");
  assert.deepEqual(JSON.parse(await (await f.store.get(f.writes.at(-1))).text()), f.manifest);
  const count = f.writes.length;
  assert.deepEqual(await publishIndexExports(f.port, f.store), { version: f.manifest.version, written: 0 });
  assert.equal(f.writes.length, count);
  assert.deepEqual(f.requests.slice(-1), ["manifest.json"]);
});
test("failed export preserves the old pointer and a retry safely reuses complete objects", async () => {
  const f = fixture(), original = f.objects["meta.json"];
  f.objects["meta.json"] = "corrupted";
  await assert.rejects(publishIndexExports(f.port, f.store));
  assert.equal(f.files.has("published/library-index/current.json"), false);
  assert.equal(f.files.has("trial/library-index/state.json.gz"), false);
  f.objects["meta.json"] = original;
  assert.equal((await publishIndexExports(f.port, f.store)).written, 1);
  assert.equal(f.writes.filter(k => k.endsWith("/all.json")).length, 1);
});
test("private paths, malformed ranges, checksums and oversized controls fail closed", async () => {
  for (const change of [m => m.files["../state.json.gz"] = m.files["all.json"], m => m.pages[0][0] = 0,
    m => m.pages[0][1]--, m => m.pages[0][1] = 512 * 1024 + 1, m => m.version = "../version", m => m.files["all.json"].size = 33 * 1024 * 1024]) {
    const f = fixture(); change(f.manifest); assert.throws(() => validateIndexManifest(f.manifest));
  }
  const f = fixture(); f.objects["manifest.json"] = " ".repeat(256 * 1024 + 1);
  await assert.rejects(publishIndexExports(f.port, f.store)); assert.deepEqual(f.writes, []);
});
test("only published IDs are listed with bounded checked pagination", async () => {
  const requests = [], store = { list: async options => {
    requests.push(options); return { objects: [{ key: `published/library/articles/${rows[requests.length - 1].id}.json` }],
      truncated: requests.length === 1, cursor: requests.length === 1 ? "next" : undefined };
  } };
  assert.deepEqual(await publishedIds(store), rows.map(r => r.id));
  assert.deepEqual(requests[1], { prefix: "published/library/articles/", limit: 1000, cursor: "next" });
  for (const page of [{ objects: [{ key: "trial/library/articles/private.json" }] }, { objects: [], truncated: true },
    { objects: [1, 1].map(() => ({ key: `published/library/articles/${rows[0].id}.json` })) }])
    await assert.rejects(publishedIds({ list: async () => page }));
});
test("Container index inputs can read canonical published articles and private index state only", async () => {
  const calls = [], env = { PUBLISH_LIBRARY_ENABLED: "true", TRIAL_STORE: { get: async key => { calls.push(key); return { size: 2, body: "{}" }; } } };
  assert.equal((await readIndexInput(new Request(`http://article-store/library/${rows[0].id}.json`), env)).status, 200);
  assert.equal(calls[0], `published/library/articles/${rows[0].id}.json`);
  assert.equal((await readIndexInput(new Request("http://article-store/index-state.json.gz"), env)).status, 200);
  assert.equal(calls[1], "trial/library-index/state.json.gz");
  for (const url of ["https://article-store/index-state.json.gz", "http://external/index-state.json.gz", "http://article-store/trial/state.json.gz", "http://article-store/index-state.json.gz?key=x", "http://article-store/library/../private.json"])
    assert.equal((await readIndexInput(new Request(url), env)).status, 403);
  assert.equal((await readIndexInput(new Request("http://article-store/index-state.json.gz", { method: "POST" }), env)).status, 403);
  assert.equal((await readIndexInput(new Request("http://article-store/index-state.json.gz"), { ...env, PUBLISH_LIBRARY_ENABLED: "false" })).status, 403);
  assert.equal(calls.length, 2);
});
test("index publication requires existing authentication and explicit publication enablement", async () => {
  let calls = 0;
  const env = { TRIAL_TOKEN: "control", PUBLISH_LIBRARY_ENABLED: "true", TRIAL_ENABLED: "false", TRIAL_CONTAINER: { getByName: name => {
    assert.equal(name, "priority-trial"); return { fetch: async (url, options) => { calls++; assert.equal(url, "http://trial/publish-library-index"); assert.equal(options.method, "POST"); return Response.json({ ok: true }); } };
  } } };
  const request = authenticated => new Request("https://trial/publish-library-index", { method: "POST", headers: authenticated ? { Authorization: "Bearer control" } : {} });
  assert.equal((await route(request(false), env)).status, 401);
  assert.equal((await route(request(true), { ...env, PUBLISH_LIBRARY_ENABLED: "false" })).status, 409);
  assert.equal((await route(request(true), env)).status, 200); assert.equal(calls, 1);
});


test("an index version cannot disguise a different file manifest", async () => {
  const f = fixture(); f.manifest.version = sha("wrong version"); f.objects["manifest.json"] = JSON.stringify(f.manifest);
  await assert.rejects(publishIndexExports(f.port, f.store)); assert.deepEqual(f.writes, []);
});
