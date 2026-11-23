import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { storeTrialLibrary, readTrialArticle, validArticle } from "./library.mjs";
import { route } from "./policy.mjs";

const rows = JSON.parse(await readFile(new URL("../../assets/globe/news-live.json", import.meta.url), "utf8")).stories.slice(0, 2);
function storage() {
  const files = new Map(), puts = [];
  return { files, puts, head: async key => files.has(key) ? {} : null,
    put: async (key, value) => { files.set(key, value); puts.push(key); },
    get: async key => files.has(key) ? { body: files.get(key) } : null };
}
function exportPage(page) { return { fetch: async url => {
  assert.equal(new URL(url).pathname, "/library");
  return Response.json(page);
} }; }

test("full real articles retain all fields and dates; existing bytes are never rewritten", async () => {
  const store = storage(), before = JSON.stringify(rows);
  const port = exportPage({ articles: rows, total: rows.length, next: rows.length });
  assert.deepEqual(await storeTrialLibrary(port, store, rows.length), { articles: rows.length, written: rows.length });
  for (const row of rows) assert.deepEqual(JSON.parse(store.files.get(`trial/library/articles/${row.id}.json`)), row);
  const old = new Map(store.files);
  assert.deepEqual(await storeTrialLibrary(exportPage({ articles: rows.map(r => ({ ...r, headline: r.headline + " " })), total: rows.length, next: rows.length }), store, rows.length), { articles: rows.length, written: 0 });
  assert.deepEqual(store.files, old);
  assert.equal(JSON.stringify(rows), before);
});
test("malformed pagination and duplicate IDs cannot advance trial state", async () => {
  for (const page of [{ articles: rows, next: 0, total: rows.length }, { articles: [], next: 0, total: rows.length },
    { articles: [rows[0], rows[0]], next: 2, total: 2 }, { articles: [{ ...rows[0], id: "../key" }], next: 1, total: 1 }]) {
    await assert.rejects(storeTrialLibrary(exportPage(page), storage(), page.total));
  }
  for (const expected of [-1, 1.5, 10001, undefined]) await assert.rejects(storeTrialLibrary({}, storage(), expected));
  assert.equal(validArticle({ ...rows[0], id: undefined }), false);
});
test("a failed or oversized export never writes its page", async () => {
  for (const response of [new Response("failed", { status: 500 }), new Response("x".repeat(6 * 1024 * 1024 + 1))]) {
    const store = storage();
    await assert.rejects(storeTrialLibrary({ fetch: async () => response }, store, 1));
    assert.deepEqual(store.puts, []);
  }
});
test("article reads require authentication, reject paths and return exact stored data", async () => {
  const store = storage();
  await storeTrialLibrary(exportPage({ articles: rows, total: rows.length, next: rows.length }), store, rows.length);
  assert.equal((await route(new Request(`https://trial/article?id=${rows[0].id}`), { TRIAL_TOKEN: "secret", TRIAL_STORE: store })).status, 401);
  for (const query of ["", "?id=../key", "?id=a&id=b", "?id=%2Fprivate"])
    assert.equal((await readTrialArticle(new Request("https://trial/article" + query), store)).status, 400);
  const response = await route(new Request(`https://trial/article?id=${rows[0].id}`, { headers: { Authorization: "Bearer secret" } }), { TRIAL_TOKEN: "secret", TRIAL_STORE: store });
  assert.equal(response.status, 200); assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(await response.json(), rows[0]);
  assert.equal((await readTrialArticle(new Request("https://trial/article?id=missing-article"), store)).status, 404);
});
