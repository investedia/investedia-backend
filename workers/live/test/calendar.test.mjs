import test from 'node:test'; import assert from 'node:assert/strict';
import { fakeKV } from './helpers.mjs'; import { ingestCalendar, readCalendar } from '../v1/calendar.js';
const rq = (b, tok = 't') => new Request('https://x/v1/ingest/calendar', { method: 'POST', body: JSON.stringify(b), headers: { Authorization: 'Bearer ' + tok } });
test('calendar ingest needs token, validates, stores and reads back', async () => {
  const env = { PRICES: fakeKV(), INGEST_TOKEN: 't' };
  assert.equal((await ingestCalendar(rq({ updated_at: 'x', events: [] }, 'bad'), env)).status, 401);
  assert.equal((await ingestCalendar(rq({ updated_at: 'x', events: [{ t: 1 }] }), env)).status, 422);
  assert.equal((await readCalendar(env)).status, 404);
  const r = await ingestCalendar(rq({ updated_at: '2026-11-10T00:00:00Z', events: [{ t: 'CPI', c: 'USD', at: '2026-11-12T13:30:00Z', imp: 3, extra: 'dropped' }] }), env);
  assert.equal(r.status, 200); const b = (await readCalendar(env)).body;
  assert.equal(b.events.length, 1); assert.equal(b.events[0].extra, undefined);
});
