import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { handleNews } from '../v1/news.js';
import { ingestLibrary } from '../v1/library.js';
import { fakeKV } from './helpers.mjs';

const saved = JSON.parse(readFileSync(new URL('../../../assets/globe/news-live.json', import.meta.url), 'utf8'));
const now = Date.parse(saved.updated_at);
const snapshot = { t: now, stories: saved.stories.slice(0, 3) };
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('news starts both independent reads before waiting for either', async () => {
  const history = deferred(), connections = deferred(), started = [];
  const env = { PRICES: { get: async key => {
    if (key === 'news') return JSON.stringify(snapshot);
    started.push(key);
    return key === 'news-gap-history' ? history.promise : connections.promise;
  } } };
  const pending = handleNews(env, now);
  try {
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(started, ['news-gap-history', 'connections:meta']);
  } finally {
    history.resolve(JSON.stringify({ stories: [] }));
    connections.resolve(JSON.stringify({ generated_at: saved.updated_at }));
  }
  const result = await pending;
  assert.equal(result.status, 200);
  assert.equal(result.body.meta.connections_generated_at, saved.updated_at);
  assert.equal(result.body.meta.fetched_at, new Date(now).toISOString());
  assert.equal(result.body.data.stories.length, snapshot.stories.length);
});

for (const broken of ['news-gap-history', 'connections:meta']) {
  for (const failure of ['unavailable', 'malformed']) {
    test(`news preserves saved articles when ${broken} is ${failure}`, async () => {
      const kv = fakeKV({news: JSON.stringify(snapshot), 'news-gap-history': '{"stories":[]}', 'connections:meta': JSON.stringify({generated_at: saved.updated_at})});
      const get = kv.get.bind(kv);
      kv.get = async key => {
        if (key !== broken) return get(key);
        if (failure === 'unavailable') throw Error('Test-only storage failure');
        return '{test-only malformed JSON';
      };
      const result = await handleNews({PRICES: kv}, now);
      assert.equal(result.status, 200);
      assert.deepEqual(result.body.data.stories.map(s => s.id).sort(), snapshot.stories.map(s => s.id).sort());
      assert.equal(result.body.meta.fetched_at, new Date(now).toISOString());
      assert.equal(result.body.meta.connections_generated_at, broken === 'connections:meta' ? null : saved.updated_at);
      assert.equal(kv.puts, 0);
    });
  }
}

test('news without a valid current feed does not read optional storage', async () => {
  for (const value of [null, '{broken', '{"stories":[]}']) {
    const keys = [];
    const result = await handleNews({PRICES: {get: async key => { keys.push(key); return value; }}}, now);
    assert.equal(result.status, 503);
    assert.deepEqual(keys, ['news']);
  }
});

// Test-only compact row, stored only in fakeKV.
const day = '2026-11-11', at = Date.parse(day + 'T12:00:00Z');
const row = {id: 'test-fixture', h: '[Test fixture] Library article', t: day + 'T01:00:00Z'};
const request = rows => new Request('https://fixture.invalid/v1/ingest/library', {
  method: 'POST', headers: {Authorization: 'Bearer test-only'}, body: JSON.stringify({days: {[day]: rows}}),
});

test('unchanged library upload reads metadata once and writes nothing', async () => {
  const kv = fakeKV(), env = {INGEST_TOKEN: 'test-only', PRICES: kv};
  await ingestLibrary(request([row]), env, at);
  const before = [...kv.m.entries()], writes = kv.puts, keys = [], get = kv.get.bind(kv);
  kv.get = async key => { keys.push(key); return get(key); };
  const result = await ingestLibrary(request([row]), env, at + 60_000);
  assert.deepEqual(keys, ['library:meta', 'library:' + day]);
  assert.equal(result.body.written, 0);
  assert.equal(kv.puts, writes);
  assert.deepEqual([...kv.m.entries()], before);
});

test('empty library initializes missing metadata with one read', async () => {
  const kv = fakeKV(), keys = [], get = kv.get.bind(kv);
  kv.get = async key => { keys.push(key); return get(key); };
  const result = await ingestLibrary(request([]), {INGEST_TOKEN: 'test-only', PRICES: kv}, at);
  assert.equal(result.status, 200);
  assert.deepEqual(keys, ['library:meta']);
  assert.equal(JSON.parse(kv.m.get('library:meta')).updated_at, new Date(at).toISOString());
});

test('failed metadata read retains the existing retry before initialization', async () => {
  const kv = fakeKV(); let reads = 0;
  kv.get = async () => { if (++reads === 1) throw Error('Test-only transient failure'); return null; };
  const result = await ingestLibrary(request([]), {INGEST_TOKEN: 'test-only', PRICES: kv}, at);
  assert.equal(result.status, 200);
  assert.equal(reads, 2);
  assert.equal(kv.puts, 1);
});
