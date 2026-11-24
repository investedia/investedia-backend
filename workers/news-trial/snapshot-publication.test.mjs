import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { publishSnapshot, SNAPSHOT_LIMIT } from "./snapshot-publication.mjs";
const markets = await readFile(new URL("../../assets/globe/markets.json", import.meta.url));
const fx = await readFile(new URL("../../tests/fixtures/cloudflare-fx-ecb.json", import.meta.url));
function setup(bytes, previous = null) {
  const writes = [];
  return { writes, port: { fetch: async () => new Response(bytes) }, env: { DATA_PUBLICATION_ENABLED: "true", TRIAL_STORE: {
    head: async () => previous, put: async (key, body, options) => writes.push({ key, body, options })
  } } };
}
test("real saved market and ECB bytes and dates remain exact, repeats write nothing", async () => {
  for (const [job, bytes, file] of [["markets", markets, "markets.json"], ["fx", fx, "fx-ecb.json"]]) {
    const b = setup(bytes), result = await publishSnapshot(b.port, b.env, job);
    assert.equal(result.written, true); assert.equal(b.writes[0].key, "published/data/" + file);
    assert.deepEqual(Buffer.from(b.writes[0].body), bytes);
    b.env.TRIAL_STORE.head = async () => ({ size: bytes.byteLength, customMetadata: b.writes[0].options.customMetadata });
    assert.equal((await publishSnapshot(b.port, b.env, job)).written, false); assert.equal(b.writes.length, 1);
  }
});
test("disabled and review-only jobs cannot fetch or write", async () => {
  for (const job of ["markets", "fx", "country-basics", "economy-history", "../private"]) {
    const b = setup(markets); b.port.fetch = async () => { throw Error("must not fetch"); };
    if (["markets", "fx"].includes(job)) b.env.DATA_PUBLICATION_ENABLED = "false";
    await assert.rejects(publishSnapshot(b.port, b.env, job)); assert.equal(b.writes.length, 0);
  }
});
test("invalid, empty, oversized and older snapshots preserve existing data", async () => {
  for (const bytes of ["{}", "invalid", JSON.stringify({ ...JSON.parse(markets), assets: [] }), new Uint8Array(SNAPSHOT_LIMIT + 1)]) {
    const b = setup(bytes); await assert.rejects(publishSnapshot(b.port, b.env, "markets")); assert.equal(b.writes.length, 0);
  }
  const b = setup(markets, { customMetadata: { asof: new Date().toISOString() } });
  await assert.rejects(publishSnapshot(b.port, b.env, "markets"), /Newer snapshot/); assert.equal(b.writes.length, 0);
});
test("failed storage is not reported as publication success", async () => {
  const b = setup(fx); b.env.TRIAL_STORE.put = async () => { throw Error("storage unavailable"); };
  await assert.rejects(publishSnapshot(b.port, b.env, "fx"));
});

test("market snapshot uses the same bounded read retry without repeating generation", async () => {
  const b = setup(markets); let calls = 0;
  b.port.fetch = async url => { assert.equal(url, "http://container/output?kind=markets"); if (++calls === 1) throw Error("private socket details"); return new Response(markets); };
  const result = await publishSnapshot(b.port, b.env, "markets");
  assert.equal(calls, 2); assert.equal(result.written, true); assert.equal(b.writes.length, 1);
  assert.deepEqual(Buffer.from(b.writes[0].body), markets);
});
