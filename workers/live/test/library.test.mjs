import test from 'node:test';
import assert from 'node:assert/strict';
import { ingestLibrary, handleLibrary } from '../v1/library.js';
const setup = () => { const map = new Map(); let writes = 0; return { map, get writes() { return writes; }, env: { INGEST_TOKEN: 't', PRICES: { get: async k => map.get(k) ?? null, put: async (k, v) => { writes++; map.set(k, v); } } } }; };
const post = (b, tok = 't') => new Request('https://x.test/v1/ingest/library', { method: 'POST', headers: { Authorization: 'Bearer ' + tok }, body: JSON.stringify(b) });
const row = (id, t, extra = {}) => ({ id, h: 'Headline ' + id, c: 'economy', t, s: 'Source', n: 'Brazil', g: 'latam', k: 2, ...extra });
const NOW = Date.parse('2026-11-11T12:00:00Z');
test('stores days, serves meta and rows newest first, rejects bad input', async () => {
  const s = setup();
  assert.equal((await ingestLibrary(post({ days: {} }, 'x'), s.env, NOW)).status, 401);
  assert.equal((await ingestLibrary(post({ days: { 'bad': [] } }), s.env, NOW)).status, 422);
  const r = await ingestLibrary(post({ days: { '2026-11-11': [row('a', '2026-11-11T01:00:00Z'), row('b', '2026-11-11T05:00:00Z'), row('a', '2026-11-11T01:00:00Z'), row('x', '2026-11-10T23:00:00Z'), row('evil', '2026-11-11T02:00:00Z', { i: '../../secret' })] } }), s.env, NOW);
  assert.equal(r.status, 200);
  const meta = (await handleLibrary(new URL('https://x/v1/library'), s.env)).body.data;
  assert.deepEqual(meta.days, { '2026-11-11': 3 });
  const day = (await handleLibrary(new URL('https://x/v1/library?day=2026-11-11'), s.env)).body.data.rows;
  assert.deepEqual(day.map(x => x.id), ['b', 'evil', 'a']); assert.equal(day[1].i, undefined);
  assert.equal((await handleLibrary(new URL('https://x/v1/library?day=2026-01-01'), s.env)).status, 404);
});
test('unchanged days cost no KV writes', async () => {
  const s = setup(), b = { days: { '2026-11-11': [row('a', '2026-11-11T01:00:00Z')] } };
  await ingestLibrary(post(b), s.env, NOW); const w = s.writes; await ingestLibrary(post(b), s.env, NOW); assert.equal(s.writes, w);
});
test('older backfilled days stay listed next to the newest days', async () => {
  const s = setup();
  for (let d = 0; d < 60; d++) {
    const day = new Date(Date.parse('2026-09-01T00:00:00Z') + d * 864e5).toISOString().slice(0, 10);
    await ingestLibrary(post({ days: { [day]: [row('n' + d, day + 'T01:00:00Z')] } }), s.env, NOW);
  }
  await ingestLibrary(post({ days: { '2026-08-14': [row('old', '2026-08-14T03:00:00Z')] } }), s.env, NOW);
  const days = (await handleLibrary(new URL('https://x/v1/library'), s.env)).body.data.days;
  assert.equal(Object.keys(days).length, 61); assert.equal(days['2026-08-14'], 1); assert.equal(days['2026-09-01'], 1);
});
